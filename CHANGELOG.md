# [1.2.0](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v1.1.0...v1.2.0) (2022-02-11)


### Bug Fixes

* **requirements:** Updated requirements to install psycopg2 in docker container correctly. ([117a610](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/117a6104d87f1bebe80f6731dee40e829537c414))


### Features

* **browsers:** Updated api ([786aadd](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/786aadd95a8339700785fc8035eab89316337b6a))
* **browsers:** Updated api ([1aa52ef](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/1aa52effd4da42a1a170202af6a3fcc90d8412a9))
* **species:** Added species clustering information. ([ed74b85](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/ed74b857742a8c1db022ad17fcb87de8281c73a9))
* **species:** Added species page. ([e4736ca](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/e4736cac16361f2f23905867af0332cf2675630f))
* **taxon:** Added /taxon/name to get descendant ranks and counts. ([910c086](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/910c086298a56ad0ce40cf65c8b5fcfcc8081c23))
* **taxonomy:** Added taxonomy count and PostgreSQL access. ([6c7bf1c](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/6c7bf1cfa3a000d0ecb3108a64797ab3617fc19c))

# [1.1.0](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v1.0.1...v1.1.0) (2021-12-01)


### Bug Fixes

* **cors:** Update CORS for local testing. ([5f45af0](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/5f45af03f11fb892a753a6f3183e9d5d75abd817))
* **fastani:** Add args to main job to prevent job arguments being passed print function. ([8540fbf](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/8540fbf79027898f50bb90dfb0abb15e7b1a3a02))
* **fastani:** CSV export would not display group_2 correctly. ([ce5f5c2](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/ce5f5c21e9ddf305f2bf7e0a8b76f8899728a635))
* **fastani:** Divergent genomes would not be reported. ([fb20f5d](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/fb20f5da1c44d8ed640f33d2f1c8003ce985bbf8))
* **fastani:** Fixed creation of result from params. ([ef9bd21](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/ef9bd21abdcb0e77125f9013ea4ffac4bcb824fb))
* **fastani:** Main job would not retain results for the specified period in the environment variable ([d4d0990](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/d4d09903c38f59e3f5f663f147a3754306d4c0d4))
* **fastani:** Updated FastANI CSV output to match table. ([3da61ed](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/3da61ed8b5a2ac70c60ee7003a14900194de6cdf))


### Features

* **fastani:** Added csv download link to retrieve results. ([94436bf](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/94436bf47996e53bac4a87756e95684fc5da7ea9))
* **fastani:** Added query and reference genomes to main job. ([26500ca](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/26500ca41228443a7fda8511919dca4f65437357))


### Reverts

* Reverting locked package versions. ([ebe4cb6](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/ebe4cb61aa1f9938bd1ac93f926fc7119df099a9))

## [1.0.1](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v1.0.0...v1.0.1) (2021-11-20)


### Bug Fixes

* **ci:** Fix semantic release substituting __version__ incorrectly. ([61acdad](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/61acdad7323fe556989667da5f53905f36938fca))

# 1.0.0 (2021-11-20)


### Features

* Initialise repository. ([4cdd834](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/4cdd834e0e15ae3a061a497085b729b0d857d95a))
