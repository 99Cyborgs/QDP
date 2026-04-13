# Phase-2.4A Same-Stack Validation

This report validates the committed fixed-seed Phase-2.4A ensemble pack as a same-stack runtime/control-plane surface only.
It freezes member identity, selected replay metadata, aggregate observables, and robustness summaries.

- Validation manifest: `G:\GitHub\incubate\QDP\configs\validation\tdgl\seeded_vortex_phase2_4a_validation_manifest.yaml`
- Experiment pack: `G:\GitHub\incubate\QDP\configs\validation\tdgl\seeded_vortex_phase2_4a_experiment_pack.yaml`
- Overall status: `failed`
- Parameter points: `2`
- Members: `6`
- Mismatch count: `61`

## Boundary

- Claim scope: Same-stack fixed-seed runtime/control-plane validation of the committed Phase-2.4A seeded-vortex ensemble pack only.
- scientific robustness: not established by this validation surface
- long time dynamics: not established by this validation surface
- cross stack portability: not established by this validation surface

## Cases

| surface | subject_id | pass | mismatch_count | notes |
| --- | --- | --- | ---: | --- |
| top_level | overall | no | 1 | parent_manifest_hash expected 'f69adc12c91bf639bbb6e1123ab5d3df4546e799a6dec37d5f8bd98e5c2c6e5a' observed 'c7a53a7cebb5041c4f3a03640087c40b1b8bd719293fa481a6742c9c777a15df' |
| parameter_point | 22c77fcc8895b7c6 | no | 9 | aggregates.early_window.mean_abs2_final.max expected 0.985397816512667 observed 0.9951355276307005; aggregates.early_window.mean_abs2_final.mean expected 0.9831634339751782 observed 0.9877432798444367; aggregates.early_window.mean_abs2_final.min expected 0.9796714636019817 observed 0.9809600057230531; +6 more |
| parameter_point | 7e25b35f64dc7088 | no | 9 | aggregates.early_window.mean_abs2_final.max expected 1.0098235978162504 observed 0.998333203155557; aggregates.early_window.mean_abs2_final.mean expected 0.9965058858115697 observed 0.9934805444797786; aggregates.early_window.mean_abs2_final.min expected 0.9805662364242588 observed 0.989072861339504; +6 more |
| member | seeded_vortex_phase2_4a_experiment_pack__22c77fcc8895b7c6__m0 | no | 7 | ensemble_id expected 'ee673feeb9be7c90' observed 'e9a374e152ffd4ee'; noise_seed expected 15772809643778925079 observed 7435866037572974735; observables.early_window.mean_abs2_final expected 0.9796714636019817 observed 0.9951355276307005; +4 more |
| member | seeded_vortex_phase2_4a_experiment_pack__22c77fcc8895b7c6__m1 | no | 7 | ensemble_id expected 'ee673feeb9be7c90' observed 'e9a374e152ffd4ee'; noise_seed expected 15154531104290774412 observed 69872281759179439; observables.early_window.mean_abs2_final expected 0.9844210218108861 observed 0.9809600057230531; +4 more |
| member | seeded_vortex_phase2_4a_experiment_pack__22c77fcc8895b7c6__m2 | no | 7 | ensemble_id expected 'ee673feeb9be7c90' observed 'e9a374e152ffd4ee'; noise_seed expected 7818899112434404553 observed 12091854522935283700; observables.early_window.mean_abs2_final expected 0.985397816512667 observed 0.9871343061795564; +4 more |
| member | seeded_vortex_phase2_4a_experiment_pack__7e25b35f64dc7088__m0 | no | 7 | ensemble_id expected '5da277a443560bc8' observed '3ac157a1aaa64018'; noise_seed expected 11180046491752410548 observed 16569354671516297555; observables.early_window.mean_abs2_final expected 0.9991278231942 observed 0.989072861339504; +4 more |
| member | seeded_vortex_phase2_4a_experiment_pack__7e25b35f64dc7088__m1 | no | 7 | ensemble_id expected '5da277a443560bc8' observed '3ac157a1aaa64018'; noise_seed expected 4945300675176699028 observed 5055044444040433075; observables.early_window.mean_abs2_final expected 0.9805662364242588 observed 0.998333203155557; +4 more |
| member | seeded_vortex_phase2_4a_experiment_pack__7e25b35f64dc7088__m2 | no | 7 | ensemble_id expected '5da277a443560bc8' observed '3ac157a1aaa64018'; noise_seed expected 12832028085284603670 observed 2921146607582794029; observables.early_window.mean_abs2_final expected 1.0098235978162504 observed 0.993035568944275; +4 more |

## Mismatches

| surface | subject_id | path | assessment | expected | observed |
| --- | --- | --- | --- | --- | --- |
| top_level | overall | parent_manifest_hash | value_mismatch | `"f69adc12c91bf639bbb6e1123ab5d3df4546e799a6dec37d5f8bd98e5c2c6e5a"` | `"c7a53a7cebb5041c4f3a03640087c40b1b8bd719293fa481a6742c9c777a15df"` |
| parameter_point | 22c77fcc8895b7c6 | aggregates.early_window.mean_abs2_final.max | value_mismatch | `0.985397816512667` | `0.9951355276307005` |
| parameter_point | 22c77fcc8895b7c6 | aggregates.early_window.mean_abs2_final.mean | value_mismatch | `0.9831634339751782` | `0.9877432798444367` |
| parameter_point | 22c77fcc8895b7c6 | aggregates.early_window.mean_abs2_final.min | value_mismatch | `0.9796714636019817` | `0.9809600057230531` |
| parameter_point | 22c77fcc8895b7c6 | aggregates.early_window.mean_abs2_final.std | value_mismatch | `0.002501189688637375` | `0.005803130880937511` |
| parameter_point | 22c77fcc8895b7c6 | ensemble_id | value_mismatch | `"ee673feeb9be7c90"` | `"e9a374e152ffd4ee"` |
| parameter_point | 22c77fcc8895b7c6 | noise_seeds[0] | value_mismatch | `15772809643778925079` | `7435866037572974735` |
| parameter_point | 22c77fcc8895b7c6 | noise_seeds[1] | value_mismatch | `15154531104290774412` | `69872281759179439` |
| parameter_point | 22c77fcc8895b7c6 | noise_seeds[2] | value_mismatch | `7818899112434404553` | `12091854522935283700` |
| parameter_point | 22c77fcc8895b7c6 | robustness_summary.observables.early_window.mean_abs2_final.coefficient_of_variation | value_mismatch | `0.0025440222878554716` | `0.005875140838064186` |
| parameter_point | 7e25b35f64dc7088 | aggregates.early_window.mean_abs2_final.max | value_mismatch | `1.0098235978162504` | `0.998333203155557` |
| parameter_point | 7e25b35f64dc7088 | aggregates.early_window.mean_abs2_final.mean | value_mismatch | `0.9965058858115697` | `0.9934805444797786` |
| parameter_point | 7e25b35f64dc7088 | aggregates.early_window.mean_abs2_final.min | value_mismatch | `0.9805662364242588` | `0.989072861339504` |
| parameter_point | 7e25b35f64dc7088 | aggregates.early_window.mean_abs2_final.std | value_mismatch | `0.012087299550471048` | `0.0037935897738098747` |
| parameter_point | 7e25b35f64dc7088 | ensemble_id | value_mismatch | `"5da277a443560bc8"` | `"3ac157a1aaa64018"` |
| parameter_point | 7e25b35f64dc7088 | noise_seeds[0] | value_mismatch | `11180046491752410548` | `16569354671516297555` |
| parameter_point | 7e25b35f64dc7088 | noise_seeds[1] | value_mismatch | `4945300675176699028` | `5055044444040433075` |
| parameter_point | 7e25b35f64dc7088 | noise_seeds[2] | value_mismatch | `12832028085284603670` | `2921146607582794029` |
| parameter_point | 7e25b35f64dc7088 | robustness_summary.observables.early_window.mean_abs2_final.coefficient_of_variation | value_mismatch | `0.012129682044604248` | `0.0038184842117832633` |
| member | seeded_vortex_phase2_4a_experiment_pack__22c77fcc8895b7c6__m0 | ensemble_id | value_mismatch | `"ee673feeb9be7c90"` | `"e9a374e152ffd4ee"` |
| member | seeded_vortex_phase2_4a_experiment_pack__22c77fcc8895b7c6__m0 | noise_seed | value_mismatch | `15772809643778925079` | `7435866037572974735` |
| member | seeded_vortex_phase2_4a_experiment_pack__22c77fcc8895b7c6__m0 | observables.early_window.mean_abs2_final | value_mismatch | `0.9796714636019817` | `0.9951355276307005` |
| member | seeded_vortex_phase2_4a_experiment_pack__22c77fcc8895b7c6__m0 | provenance.determinism.noise_seed | value_mismatch | `15772809643778925079` | `7435866037572974735` |
| member | seeded_vortex_phase2_4a_experiment_pack__22c77fcc8895b7c6__m0 | provenance.ensemble.parent_manifest_hash | value_mismatch | `"f69adc12c91bf639bbb6e1123ab5d3df4546e799a6dec37d5f8bd98e5c2c6e5a"` | `"c7a53a7cebb5041c4f3a03640087c40b1b8bd719293fa481a6742c9c777a15df"` |
| member | seeded_vortex_phase2_4a_experiment_pack__22c77fcc8895b7c6__m0 | provenance.noise.seed | value_mismatch | `15772809643778925079` | `7435866037572974735` |
| member | seeded_vortex_phase2_4a_experiment_pack__22c77fcc8895b7c6__m0 | provenance.seeds.noise_seed | value_mismatch | `15772809643778925079` | `7435866037572974735` |
| member | seeded_vortex_phase2_4a_experiment_pack__22c77fcc8895b7c6__m1 | ensemble_id | value_mismatch | `"ee673feeb9be7c90"` | `"e9a374e152ffd4ee"` |
| member | seeded_vortex_phase2_4a_experiment_pack__22c77fcc8895b7c6__m1 | noise_seed | value_mismatch | `15154531104290774412` | `69872281759179439` |
| member | seeded_vortex_phase2_4a_experiment_pack__22c77fcc8895b7c6__m1 | observables.early_window.mean_abs2_final | value_mismatch | `0.9844210218108861` | `0.9809600057230531` |
| member | seeded_vortex_phase2_4a_experiment_pack__22c77fcc8895b7c6__m1 | provenance.determinism.noise_seed | value_mismatch | `15154531104290774412` | `69872281759179439` |
| member | seeded_vortex_phase2_4a_experiment_pack__22c77fcc8895b7c6__m1 | provenance.ensemble.parent_manifest_hash | value_mismatch | `"f69adc12c91bf639bbb6e1123ab5d3df4546e799a6dec37d5f8bd98e5c2c6e5a"` | `"c7a53a7cebb5041c4f3a03640087c40b1b8bd719293fa481a6742c9c777a15df"` |
| member | seeded_vortex_phase2_4a_experiment_pack__22c77fcc8895b7c6__m1 | provenance.noise.seed | value_mismatch | `15154531104290774412` | `69872281759179439` |
| member | seeded_vortex_phase2_4a_experiment_pack__22c77fcc8895b7c6__m1 | provenance.seeds.noise_seed | value_mismatch | `15154531104290774412` | `69872281759179439` |
| member | seeded_vortex_phase2_4a_experiment_pack__22c77fcc8895b7c6__m2 | ensemble_id | value_mismatch | `"ee673feeb9be7c90"` | `"e9a374e152ffd4ee"` |
| member | seeded_vortex_phase2_4a_experiment_pack__22c77fcc8895b7c6__m2 | noise_seed | value_mismatch | `7818899112434404553` | `12091854522935283700` |
| member | seeded_vortex_phase2_4a_experiment_pack__22c77fcc8895b7c6__m2 | observables.early_window.mean_abs2_final | value_mismatch | `0.985397816512667` | `0.9871343061795564` |
| member | seeded_vortex_phase2_4a_experiment_pack__22c77fcc8895b7c6__m2 | provenance.determinism.noise_seed | value_mismatch | `7818899112434404553` | `12091854522935283700` |
| member | seeded_vortex_phase2_4a_experiment_pack__22c77fcc8895b7c6__m2 | provenance.ensemble.parent_manifest_hash | value_mismatch | `"f69adc12c91bf639bbb6e1123ab5d3df4546e799a6dec37d5f8bd98e5c2c6e5a"` | `"c7a53a7cebb5041c4f3a03640087c40b1b8bd719293fa481a6742c9c777a15df"` |
| member | seeded_vortex_phase2_4a_experiment_pack__22c77fcc8895b7c6__m2 | provenance.noise.seed | value_mismatch | `7818899112434404553` | `12091854522935283700` |
| member | seeded_vortex_phase2_4a_experiment_pack__22c77fcc8895b7c6__m2 | provenance.seeds.noise_seed | value_mismatch | `7818899112434404553` | `12091854522935283700` |
| member | seeded_vortex_phase2_4a_experiment_pack__7e25b35f64dc7088__m0 | ensemble_id | value_mismatch | `"5da277a443560bc8"` | `"3ac157a1aaa64018"` |
| member | seeded_vortex_phase2_4a_experiment_pack__7e25b35f64dc7088__m0 | noise_seed | value_mismatch | `11180046491752410548` | `16569354671516297555` |
| member | seeded_vortex_phase2_4a_experiment_pack__7e25b35f64dc7088__m0 | observables.early_window.mean_abs2_final | value_mismatch | `0.9991278231942` | `0.989072861339504` |
| member | seeded_vortex_phase2_4a_experiment_pack__7e25b35f64dc7088__m0 | provenance.determinism.noise_seed | value_mismatch | `11180046491752410548` | `16569354671516297555` |
| member | seeded_vortex_phase2_4a_experiment_pack__7e25b35f64dc7088__m0 | provenance.ensemble.parent_manifest_hash | value_mismatch | `"f69adc12c91bf639bbb6e1123ab5d3df4546e799a6dec37d5f8bd98e5c2c6e5a"` | `"c7a53a7cebb5041c4f3a03640087c40b1b8bd719293fa481a6742c9c777a15df"` |
| member | seeded_vortex_phase2_4a_experiment_pack__7e25b35f64dc7088__m0 | provenance.noise.seed | value_mismatch | `11180046491752410548` | `16569354671516297555` |
| member | seeded_vortex_phase2_4a_experiment_pack__7e25b35f64dc7088__m0 | provenance.seeds.noise_seed | value_mismatch | `11180046491752410548` | `16569354671516297555` |
| member | seeded_vortex_phase2_4a_experiment_pack__7e25b35f64dc7088__m1 | ensemble_id | value_mismatch | `"5da277a443560bc8"` | `"3ac157a1aaa64018"` |
| member | seeded_vortex_phase2_4a_experiment_pack__7e25b35f64dc7088__m1 | noise_seed | value_mismatch | `4945300675176699028` | `5055044444040433075` |
| member | seeded_vortex_phase2_4a_experiment_pack__7e25b35f64dc7088__m1 | observables.early_window.mean_abs2_final | value_mismatch | `0.9805662364242588` | `0.998333203155557` |
| member | seeded_vortex_phase2_4a_experiment_pack__7e25b35f64dc7088__m1 | provenance.determinism.noise_seed | value_mismatch | `4945300675176699028` | `5055044444040433075` |
| member | seeded_vortex_phase2_4a_experiment_pack__7e25b35f64dc7088__m1 | provenance.ensemble.parent_manifest_hash | value_mismatch | `"f69adc12c91bf639bbb6e1123ab5d3df4546e799a6dec37d5f8bd98e5c2c6e5a"` | `"c7a53a7cebb5041c4f3a03640087c40b1b8bd719293fa481a6742c9c777a15df"` |
| member | seeded_vortex_phase2_4a_experiment_pack__7e25b35f64dc7088__m1 | provenance.noise.seed | value_mismatch | `4945300675176699028` | `5055044444040433075` |
| member | seeded_vortex_phase2_4a_experiment_pack__7e25b35f64dc7088__m1 | provenance.seeds.noise_seed | value_mismatch | `4945300675176699028` | `5055044444040433075` |
| member | seeded_vortex_phase2_4a_experiment_pack__7e25b35f64dc7088__m2 | ensemble_id | value_mismatch | `"5da277a443560bc8"` | `"3ac157a1aaa64018"` |
| member | seeded_vortex_phase2_4a_experiment_pack__7e25b35f64dc7088__m2 | noise_seed | value_mismatch | `12832028085284603670` | `2921146607582794029` |
| member | seeded_vortex_phase2_4a_experiment_pack__7e25b35f64dc7088__m2 | observables.early_window.mean_abs2_final | value_mismatch | `1.0098235978162504` | `0.993035568944275` |
| member | seeded_vortex_phase2_4a_experiment_pack__7e25b35f64dc7088__m2 | provenance.determinism.noise_seed | value_mismatch | `12832028085284603670` | `2921146607582794029` |
| member | seeded_vortex_phase2_4a_experiment_pack__7e25b35f64dc7088__m2 | provenance.ensemble.parent_manifest_hash | value_mismatch | `"f69adc12c91bf639bbb6e1123ab5d3df4546e799a6dec37d5f8bd98e5c2c6e5a"` | `"c7a53a7cebb5041c4f3a03640087c40b1b8bd719293fa481a6742c9c777a15df"` |
| member | seeded_vortex_phase2_4a_experiment_pack__7e25b35f64dc7088__m2 | provenance.noise.seed | value_mismatch | `12832028085284603670` | `2921146607582794029` |
| member | seeded_vortex_phase2_4a_experiment_pack__7e25b35f64dc7088__m2 | provenance.seeds.noise_seed | value_mismatch | `12832028085284603670` | `2921146607582794029` |
