[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$SweepSpecPath,

    [Parameter()]
    [string]$OutputPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    throw $Message
}

function Clone-Object {
    param(
        [Parameter(Mandatory = $true)]
        [object]$InputObject
    )

    return ($InputObject | ConvertTo-Json -Depth 100 | ConvertFrom-Json)
}

function To-DoubleArray {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Values
    )

    $result = New-Object System.Collections.Generic.List[double]
    foreach ($value in @($Values)) {
        $result.Add([double]$value)
    }

    return $result.ToArray()
}

function Test-ApproxEqual {
    param(
        [Parameter(Mandatory = $true)]
        [double]$Left,

        [Parameter(Mandatory = $true)]
        [double]$Right,

        [double]$Tolerance = 1.0e-9
    )

    return [Math]::Abs($Left - $Right) -le $Tolerance
}

function Test-ContainsValue {
    param(
        [Parameter(Mandatory = $true)]
        [double[]]$Values,

        [Parameter(Mandatory = $true)]
        [double]$Target
    )

    foreach ($value in $Values) {
        if (Test-ApproxEqual -Left $value -Right $Target) {
            return $true
        }
    }

    return $false
}

function Test-Subset {
    param(
        [Parameter(Mandatory = $true)]
        [double[]]$Subset,

        [Parameter(Mandatory = $true)]
        [double[]]$Superset
    )

    foreach ($value in $Subset) {
        if (-not (Test-ContainsValue -Values $Superset -Target $value)) {
            return $false
        }
    }

    return $true
}

function Get-MaxAbs {
    param(
        [Parameter(Mandatory = $true)]
        [double[]]$Values
    )

    $maxAbs = 0.0
    foreach ($value in $Values) {
        $candidate = [Math]::Abs($value)
        if ($candidate -gt $maxAbs) {
            $maxAbs = $candidate
        }
    }

    return $maxAbs
}

function Compress-Consecutive {
    param(
        [Parameter(Mandatory = $true)]
        [double[]]$Values
    )

    $compressed = New-Object System.Collections.Generic.List[double]
    foreach ($value in $Values) {
        if ($compressed.Count -eq 0 -or -not (Test-ApproxEqual -Left $compressed[$compressed.Count - 1] -Right $value)) {
            $compressed.Add($value)
        }
    }

    return $compressed.ToArray()
}

function Test-SymmetricLoop {
    param(
        [Parameter(Mandatory = $true)]
        [double[]]$FieldSteps,

        [Parameter(Mandatory = $true)]
        [double]$ExpectedBMax
    )

    $steps = Compress-Consecutive -Values $FieldSteps
    if ($steps.Count -lt 5) {
        return $false
    }

    if (-not (Test-ApproxEqual -Left $steps[0] -Right 0.0)) {
        return $false
    }

    if (-not (Test-ApproxEqual -Left $steps[$steps.Count - 1] -Right 0.0)) {
        return $false
    }

    $zeroIndices = New-Object System.Collections.Generic.List[int]
    for ($i = 0; $i -lt $steps.Count; $i++) {
        if (Test-ApproxEqual -Left $steps[$i] -Right 0.0) {
            $zeroIndices.Add($i)
        }
    }

    if ($zeroIndices.Count -ne 3) {
        return $false
    }

    $positiveStart = $zeroIndices[0] + 1
    $positiveEnd = $zeroIndices[1] - 1
    $negativeStart = $zeroIndices[1] + 1
    $negativeEnd = $zeroIndices[2] - 1

    if ($positiveStart -gt $positiveEnd -or $negativeStart -gt $negativeEnd) {
        return $false
    }

    $positiveSeen = $false
    for ($i = $positiveStart; $i -le $positiveEnd; $i++) {
        if ($steps[$i] -le 0.0) {
            return $false
        }

        if (Test-ApproxEqual -Left $steps[$i] -Right $ExpectedBMax) {
            $positiveSeen = $true
        }
    }

    $negativeSeen = $false
    for ($i = $negativeStart; $i -le $negativeEnd; $i++) {
        if ($steps[$i] -ge 0.0) {
            return $false
        }

        if (Test-ApproxEqual -Left $steps[$i] -Right (-1.0 * $ExpectedBMax)) {
            $negativeSeen = $true
        }
    }

    return $positiveSeen -and $negativeSeen
}

function Test-HardwareBlockShape {
    param(
        [Parameter(Mandatory = $true)]
        [object]$HardwareBinding
    )

    if ($null -eq $HardwareBinding.PSObject.Properties["target_device_ids"]) {
        return $false
    }

    if ($null -eq $HardwareBinding.PSObject.Properties["witness_channel_id"]) {
        return $false
    }

    if ($null -eq $HardwareBinding.PSObject.Properties["matched_geometry_device_ids"]) {
        return $false
    }

    return $true
}

function Get-CandidatePacket {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Template,

        [Parameter(Mandatory = $true)]
        [string]$FieldUnit,

        [Parameter(Mandatory = $true)]
        [string]$DwellTimeUnit,

        [Parameter(Mandatory = $true)]
        [double]$BMax,

        [Parameter(Mandatory = $true)]
        [double]$FcField,

        [Parameter(Mandatory = $true)]
        [double[]]$FieldSteps,

        [Parameter(Mandatory = $true)]
        [double]$OnsetField,

        [Parameter(Mandatory = $true)]
        [double]$HighField,

        [Parameter(Mandatory = $true)]
        [double[]]$DwellTimes,

        [Parameter()]
        [object]$FixedHardwareBinding
    )

    if ($FcField -eq 0.0) {
        return $null
    }

    if ([Math]::Abs($OnsetField) -le 0.0) {
        return $null
    }

    if ([Math]::Abs($HighField) -le 0.0) {
        return $null
    }

    if ([Math]::Abs($HighField) -le [Math]::Abs($OnsetField)) {
        return $null
    }

    if ($DwellTimes.Count -ne 3) {
        return $null
    }

    if (-not (Test-SymmetricLoop -FieldSteps $FieldSteps -ExpectedBMax $BMax)) {
        return $null
    }

    if (-not (Test-ContainsValue -Values $FieldSteps -Target $OnsetField)) {
        return $null
    }

    if (-not (Test-ContainsValue -Values $FieldSteps -Target $HighField)) {
        return $null
    }

    $selectedFields = @([double]0.0, [double]$OnsetField, [double]$HighField)
    $probeFields = @([double]0.0, [double]$OnsetField, [double]$HighField)

    if (-not (Test-Subset -Subset $selectedFields -Superset $FieldSteps)) {
        return $null
    }

    $packet = Clone-Object -InputObject $Template
    $packet.binding_context = "PRE_RUN_MINIMUM_ACQUISITION"
    $packet.binding_status = "TEMPLATE_UNBOUND"

    if ($null -ne $FixedHardwareBinding) {
        $packet.hardware_binding.target_device_ids = @($FixedHardwareBinding.target_device_ids)
        $packet.hardware_binding.witness_channel_id = $FixedHardwareBinding.witness_channel_id
        $packet.hardware_binding.matched_geometry_device_ids = @($FixedHardwareBinding.matched_geometry_device_ids)
    }

    $packet.field_program.field_unit = $FieldUnit
    $packet.field_program.B_max = $BMax
    $packet.field_program.fc_field = $FcField
    $packet.field_program.field_steps = @($FieldSteps)
    $packet.field_program.selected_fields = @($selectedFields)
    $packet.field_program.dwell_probe_schedule.probe_fields = @($probeFields)
    $packet.field_program.dwell_probe_schedule.dwell_times = @($DwellTimes)
    $packet.field_program.dwell_probe_schedule.dwell_time_unit = $DwellTimeUnit
    $packet.field_program.production_dwell_t_conv = $null

    $packet.cooldown_id = $null
    $packet.run_metadata.operator = $null
    $packet.run_metadata.run_date = $null
    $packet.run_metadata.lab_location = $null

    $packet.fixed_settings.T_base = $null
    $packet.fixed_settings.P_read = $null
    $packet.fixed_settings.readout_tone_id = $null
    $packet.fixed_settings.attenuation_state = $null
    $packet.fixed_settings.readout_chain_config = $null

    $packet.data_capture.raw_data_output_path = $null
    $packet.data_capture.metadata_output_path = $null
    $packet.data_capture.witness_trace_output_path = $null

    $packet.binding_checks.selected_fields_subset_of_field_steps = $true
    $packet.binding_checks.probe_schedule_lengths_match = $true
    $packet.binding_checks.field_unit_consistent = $true
    $packet.binding_checks.p_read_device_calibrated = $false
    $packet.binding_checks.output_paths_exist = $false

    $generatedNotes = New-Object System.Collections.Generic.List[string]
    foreach ($note in @($packet.notes)) {
        $generatedNotes.Add([string]$note)
    }
    $generatedNotes.Add("Generated candidate packet. Non-authoritative until merged with real hardware provenance and written into the authoritative run-binding record.")
    $generatedNotes.Add("This candidate satisfies static pre-run field and dwell checks only. It does not justify PRE_RUN_MINIMUM_READY without explicit hardware binding.")
    $packet.notes = @($generatedNotes)

    return $packet
}

function Resolve-PathString {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    return [System.IO.Path]::GetFullPath($Path)
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$templatePath = Join-Path $scriptRoot "e01_mm_first_cooldown_run_binding.json"
$executionSheetPath = Join-Path $scriptRoot "e01_mm_first_cooldown_execution_sheet.md"

if (-not (Test-Path -LiteralPath $SweepSpecPath)) {
    Fail "SweepSpecPath does not exist: $SweepSpecPath"
}

if (-not (Test-Path -LiteralPath $templatePath)) {
    Fail "Template run-binding JSON is missing: $templatePath"
}

$template = Get-Content -LiteralPath $templatePath -Raw | ConvertFrom-Json
$spec = Get-Content -LiteralPath $SweepSpecPath -Raw | ConvertFrom-Json

foreach ($propertyName in @(
    "field_unit",
    "B_max_values",
    "fc_field_values",
    "field_step_loops",
    "onset_fields",
    "high_field_selections",
    "dwell_time_ladders",
    "dwell_time_unit"
)) {
    if ($null -eq $spec.PSObject.Properties[$propertyName]) {
        Fail "Sweep spec is missing required property: $propertyName"
    }
}

$fieldUnit = [string]$spec.field_unit
$dwellTimeUnit = [string]$spec.dwell_time_unit
if ([string]::IsNullOrWhiteSpace($fieldUnit)) {
    Fail "field_unit must be non-empty."
}

if ([string]::IsNullOrWhiteSpace($dwellTimeUnit)) {
    Fail "dwell_time_unit must be non-empty."
}

$candidateBMaxValues = To-DoubleArray -Values $spec.B_max_values
$candidateFcFieldValues = To-DoubleArray -Values $spec.fc_field_values
$candidateOnsetFields = To-DoubleArray -Values $spec.onset_fields
$candidateHighFields = To-DoubleArray -Values $spec.high_field_selections
$dwellTimeLadders = @()
foreach ($ladder in @($spec.dwell_time_ladders)) {
    $dwellTimeLadders += ,(To-DoubleArray -Values $ladder)
}

$fixedHardwareBinding = $null
if ($null -ne $spec.PSObject.Properties["fixed_hardware_binding"]) {
    if (-not (Test-HardwareBlockShape -HardwareBinding $spec.fixed_hardware_binding)) {
        Fail "fixed_hardware_binding must include target_device_ids, witness_channel_id, and matched_geometry_device_ids."
    }

    $fixedHardwareBinding = Clone-Object -InputObject $spec.fixed_hardware_binding
}

$candidates = New-Object System.Collections.Generic.List[object]
foreach ($rawLoop in @($spec.field_step_loops)) {
    $fieldSteps = To-DoubleArray -Values $rawLoop
    if ($fieldSteps.Count -eq 0) {
        continue
    }

    $loopBMax = Get-MaxAbs -Values $fieldSteps
    if (-not (Test-ContainsValue -Values $candidateBMaxValues -Target $loopBMax)) {
        continue
    }

    foreach ($fcField in $candidateFcFieldValues) {
        if (Test-ApproxEqual -Left $fcField -Right 0.0) {
            continue
        }

        foreach ($onsetField in $candidateOnsetFields) {
            foreach ($highField in $candidateHighFields) {
                foreach ($dwellTimes in $dwellTimeLadders) {
                    $candidate = Get-CandidatePacket `
                        -Template $template `
                        -FieldUnit $fieldUnit `
                        -DwellTimeUnit $dwellTimeUnit `
                        -BMax $loopBMax `
                        -FcField $fcField `
                        -FieldSteps $fieldSteps `
                        -OnsetField $onsetField `
                        -HighField $highField `
                        -DwellTimes $dwellTimes `
                        -FixedHardwareBinding $fixedHardwareBinding

                    if ($null -ne $candidate) {
                        $candidates.Add($candidate)
                    }
                }
            }
        }
    }
}

if ($candidates.Count -eq 0) {
    $resultJson = "[]"
}
else {
    $resultJson = ConvertTo-Json -InputObject ($candidates.ToArray()) -Depth 100
}

if ($PSBoundParameters.ContainsKey("OutputPath")) {
    $resolvedOutputPath = Resolve-PathString -Path $OutputPath
    $resolvedTemplatePath = Resolve-PathString -Path $templatePath
    $resolvedExecutionSheetPath = Resolve-PathString -Path $executionSheetPath

    if ($resolvedOutputPath -eq $resolvedTemplatePath) {
        Fail "OutputPath must not overwrite the authoritative run-binding JSON."
    }

    if ($resolvedOutputPath -eq $resolvedExecutionSheetPath) {
        Fail "OutputPath must not overwrite the execution sheet."
    }

    $parentPath = Split-Path -Parent $resolvedOutputPath
    if ([string]::IsNullOrWhiteSpace($parentPath) -or -not (Test-Path -LiteralPath $parentPath)) {
        Fail "OutputPath parent directory does not exist: $parentPath"
    }

    Set-Content -LiteralPath $resolvedOutputPath -Value $resultJson
}
else {
    $resultJson
}
