## [2.25.1](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.25.0...v2.25.1) (2026-01-08)


### Bug Fixes

* **genome:** Correct query execution for genome retrieval ([8741285](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/87412857d40a2574c9165e8c48ba366472424180))

# [2.25.0](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.24.1...v2.25.0) (2025-12-11)


### Bug Fixes

* **build:** Update poetry to match NGINX unit. ([d335074](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/d335074f3d39f40a8e77ee0e593f1c4497e038c7))
* **build:** Update poetry to match NGINX unit. ([4ca4658](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/4ca4658519af3d9f790eff7dc744959352dc87ef))
* **build:** Update poetry to match NGINX unit. ([57f0376](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/57f0376037e93e41da5e753f4c632562ede5b426))
* **cors:**  Remove doubled definition. ([77f5168](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/77f5168673ea25dd160a4c66877666b401c23565))
* **cors:** Remove fastapi cors. ([f6aec76](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/f6aec765b1c12574e9538d7a157c4596f3a208f2))
* **skani:**  Allow user uploading. ([13bbf78](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/13bbf78ca488d9f1cfded51ca4ff0e0138a5376b))
* **skani:** Visualise heatmap on clustering sparse matrix. ([4e38902](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/4e38902df4c2d56771e38fe92aed84c22461bdf0))
* **upload:** Error handling for file upoads. ([84b7526](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/84b7526cdb2ce6e2e1e75118ffc6d9e507cad0fd))


### Features

* **ani:** Add missing features. ([c39360b](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/c39360be13aac4b4a0186b1ba279cc5265cf8972))
* **ani:** Add missing features. ([b75cd25](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/b75cd25b5bf3abddf807b942947a0e3141d81d96))
* **ani:** Update ANI calculator for skani. ([12388a9](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/12388a99085e95d46aefa2ab151bdc50a1656289))
* **skani:** Add skani model definition. ([9fd85db](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/9fd85dbb6c0c3d529ea6f1aa1446e215b9b7ea56))

## [2.24.1](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.24.0...v2.24.1) (2025-11-12)


### Bug Fixes

* **taxon:** Database update to correct s__Haloarcula marismortui being incorrectly labelled type material. ([b0c5c07](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/b0c5c07ea6e799c47f1cdd949cc51c49e08600d7))

# [2.24.0](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.23.0...v2.24.0) (2025-08-29)


### Features

* **db:** Update version to reflect database changes. ([02d3246](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/02d3246761eb031f36233608297c21509a0a60af))

# [2.23.0](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.22.0...v2.23.0) (2025-08-27)


### Features

* **tree:** Update tree links to external DBs. ([26f4cac](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/26f4cacfd504b5c034ceb1fb2ed4734ed947e30a))

# [2.22.0](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.21.1...v2.22.0) (2025-08-26)


### Features

* **tree:** Update tree links to external DBs. ([73f3630](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/73f363045fb73f6cb32e234b879db3befd1b8636))

## [2.21.1](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.21.0...v2.21.1) (2025-04-16)


### Bug Fixes

* **taxon:** Add R226 ([400c969](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/400c9695a696038e07c62fbb36537355236954fa))

# [2.21.0](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.20.4...v2.21.0) (2025-04-16)


### Features

* **R226:** Update for R226. ([9c109d0](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/9c109d08013aac49aa47f861f5c63ef325633d4d))

## [2.20.4](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.20.3...v2.20.4) (2024-09-03)


### Bug Fixes

* **ncbi_type_material:** Update type material designation in general search. ([f4650c6](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/f4650c611f964799e99791a7cefef8d6ae75654d))

## [2.20.3](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.20.2...v2.20.3) (2024-07-14)


### Bug Fixes

* **g__Dietzia:** Tree view incorrectly displayed s__Dietzia cinnamea as type of genus. Bumping to refresh cache. ([412999b](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/412999bce152610c1fcb9e319fd6f00c562917b6))

## [2.20.2](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.20.1...v2.20.2) (2024-07-11)


### Bug Fixes

* **fastapi:** Increase number of procs. ([875bfc3](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/875bfc3e41ca5af61a1eeb7b79be7061b33df474))

## [2.20.1](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.20.0...v2.20.1) (2024-05-01)


### Bug Fixes

* **sitemap:** Remove async call to sync function. ([f02a0c0](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/f02a0c08935ebc72bab6cab4950a06380be390c9))

# [2.20.0](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.19.0...v2.20.0) (2024-04-23)


### Bug Fixes

* **search:** Fix results not sorting. ([7d5228d](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/7d5228d5831cbf378b6fd9aa51732fc403e24d9a))
* **tree:** Fix duplication of genome accessions. ([3001333](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/30013338e26f0c420de2c8f3c57d90e2241d6c56))


### Features

* **fastani:** Increase maximum number of pairwise comparisons to 3000. ([9e491af](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/9e491afb1dd8706b6f62d1c1bb5ab48483bab18a))
* **R220:** Update for R220. ([d5aa008](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/d5aa008d2878fc13aa8984d9f29ce7ed21f8969e))
* **R220:** Update for R220. ([19aaa5e](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/19aaa5e8466f2f798e2a8f0ea460be8e86814341))


### Performance Improvements

* **advanced:** Update advanced search to use a materialized view. ([30bbacf](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/30bbacf8eeb8d0b2fddc01f6ccee5969b75623d9))

# [2.19.0](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.18.4...v2.19.0) (2024-03-06)


### Features

* **fastani:** Update FastANI calculator API. ([0c9c4d3](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/0c9c4d382eed1b3db2b5cd547eef37ab89d6b7cb))

## [2.18.4](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.18.3...v2.18.4) (2024-02-22)


### Bug Fixes

* **plausible:** Update Plausible to new domain name. ([e255a23](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/e255a23aec7298512287b6b6f2826fb412aa3343))

## [2.18.3](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.18.2...v2.18.3) (2024-02-22)


### Bug Fixes

* **status:** Scale database time to milliseconds. ([03bb1a4](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/03bb1a40aa3d850e0a0c026d01d0a4d689162c9f))

## [2.18.2](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.18.1...v2.18.2) (2023-12-10)


### Bug Fixes

* **db:** Increase connection pool size. ([d710ee3](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/d710ee384428566d751170d2c6646b06f29313b8))

## [2.18.1](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.18.0...v2.18.1) (2023-09-28)


### Bug Fixes

* **db:** Increase connection pool size due to timeouts. ([7f25d4a](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/7f25d4a6395f6af627b67457792c9e4bfff8f0a5))

# [2.18.0](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.17.0...v2.18.0) (2023-09-28)


### Features

* **fastani:** Reduce max FastANI pairwise comparisons to 5000. ([e643a81](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/e643a81e48fe4c1af43b62413f88371c6e378f42))

# [2.17.0](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.16.0...v2.17.0) (2023-04-28)


### Bug Fixes

* **R214:** Update API for GTDB R214. ([b999299](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/b999299871704ab670452fdbb6e058da1159ba9e))
* **R214:** Update API for GTDB R214. ([dd41925](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/dd4192501c02c7d30f61cc9cd5b038a7797c52ce))


### Features

* **R214:** Update API for GTDB R214. ([6ffe684](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/6ffe6846e135a6790cb781283fd42ca0d3efd617))

# [2.16.0](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.15.0...v2.16.0) (2023-04-14)


### Features

* **lpsn:** Update LPSN scraping to use DB backend. ([9677ae5](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/9677ae58c9a286e3cfb7c32051d1ad68589025bf))

# [2.15.0](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.14.0...v2.15.0) (2023-04-05)


### Bug Fixes

* **fastani:** Filter out genomes that do not exist in the database. ([b9396c7](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/b9396c7d4188cf1de2f799318331d8c9247293ea))


### Features

* **taxon:** Add additional data for taxon card ([f611821](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/f6118210e7798354109a03646193d39eddcf144e))

# [2.14.0](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.13.0...v2.14.0) (2023-04-04)


### Features

* **tree:** Add NCBI URL to taxon. ([d236e33](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/d236e335772d41a155509c64a84d71500d7bde5c))

# [2.13.0](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.12.2...v2.13.0) (2023-04-03)


### Features

* **fastani:** Add method to find previous jobs. ([131c2dd](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/131c2ddc289e712bb8fa6a73515a1953dfd31398))
* **tree:** Add LPSN URL to taxon. ([54b9d08](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/54b9d08a5afa57c6c5b29ab764a82ed13e052370))

## [2.12.2](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.12.1...v2.12.2) (2023-04-02)


### Bug Fixes

* **fastani:** Await e-mail function. ([f504a5b](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/f504a5b1739f90c04f56fcbdd0b48b724b475f75))

## [2.12.1](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.12.0...v2.12.1) (2023-04-02)


### Bug Fixes

* **fastani:** Await e-mail function. ([f33f3bc](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/f33f3bca223d61da037b32c769d40709e5aa3711))

# [2.12.0](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.11.0...v2.12.0) (2023-04-02)


### Bug Fixes

* **fastani:** Set maximum amount of jobs for low priority queue. ([ae64f1b](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/ae64f1b19e34b62e46cc97c34b0ab603b8fa4c05))


### Features

* **fastani:** Add option to have results e-mailed to the user. ([379a6b7](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/379a6b7d1a80a8787e8aa32a933318e30dd9101f))

# [2.11.0](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.10.0...v2.11.0) (2023-03-28)


### Features

* **fastani:** Add low priority queue. ([1f2acc1](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/1f2acc1e081e841fdeefe7797a8a084a3c8173b0))

# [2.10.0](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.9.0...v2.10.0) (2023-03-26)


### Features

* **previous-releases:** Add pagination to previous releases modal. ([95d9bbd](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/95d9bbdc5c275d08a283c985da7ecdf395ab13b0))
* **taxon:** Add API to obtain GC count histogram bins for a specific taxon. ([3cd0d30](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/3cd0d30fd1c9a2062b062fad7b9ac75a3c5cc7b6))

# [2.9.0](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.8.0...v2.9.0) (2023-03-19)


### Features

* **cache:** Add permanent caching for requests that provide a cacheKey. ([0c97204](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/0c972045ca43f0f2d7428309452a5e7af9531fd9))
* **fastani:** Ignore plot when clustering. ([67aca84](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/67aca8427423b57512bec4c05470ebb16a22eef5))

# [2.8.0](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.7.0...v2.8.0) (2023-03-17)


### Features

* **advanced:** API to generate shell script for downloading NCBI genomes. ([a930790](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/a930790f85ef68f3b79be3911054b540fd991a02))

# [2.7.0](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.6.0...v2.7.0) (2023-03-15)


### Features

* **sitemap:** Add tree to sitemap. ([b94a774](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/b94a774c883b14b7f0b41bf16eac83e3c3577deb))

# [2.6.0](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.5.0...v2.6.0) (2023-03-12)


### Features

* **email:** Add blacklisted e-mails to contact us. ([bdc517a](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/bdc517ab8fbd642671d5ce3a0d630a720c77bc17))

# [2.5.0](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.4.0...v2.5.0) (2023-02-15)


### Features

* **sitemap:** Add endpoint for sitemap generation. ([31699f7](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/31699f7ff1d6a0bb6015fada5843b2d0f8131631))

# [2.4.0](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.3.0...v2.4.0) (2023-02-15)


### Features

* **sitemap:** Add endpoint for sitemap generation. ([730488a](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/730488a444ed88c3a9212777b2aaa970d865f4e6))

# [2.3.0](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.2.0...v2.3.0) (2023-01-30)


### Features

* **plausible:** Add plausible analytics. ([0d33a0b](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/0d33a0b93617ff058cb1f97c066d4e38ee0fde35))
* **plausible:** Add plausible analytics. ([fa80882](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/fa808829b1b85be4780f189527248290f8af753d))
* **plausible:** Add plausible analytics. ([25c6b07](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/25c6b0744c5c51bc4d13c6842d50dd294dfbfb53))
* **tree:** Add Bergey's Manual column to taxon schema. ([013855c](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/013855c93281f3db7b3536d6043cc01e2f6c8f8a))
* **tree:** Add SeqCode column to taxon schema. ([197d97c](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/197d97c68b24eec35c8876bcbbad807d0253448b))

# [2.2.0](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.1.0...v2.2.0) (2022-10-28)


### Bug Fixes

* **survey:** Add partial searches for surveillance genome to result. ([3f7d16a](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/3f7d16ab5b5175aef211c0a431c988e31d970276))


### Features

* **tree:** Add taxon count to tree view. ([a15c05a](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/a15c05aba6afa2177f16fc5522db3dc86adbab40))


### Reverts

* Revert "fix(genome): Updated GTDB type material designation (tmp)." ([a4fafda](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/a4fafda5c3f88a639ee1f5b5ed7a6d3fd7704e38))

# [2.1.0](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.0.2...v2.1.0) (2022-06-10)


### Features

* **fastani:** Add endpoint to return heatmap data. ([373ee9a](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/373ee9a8af311d625d61a5ee6943142fe25d0a06))
* **fastani:** Add progress bar and handle single comparison case. ([d51e80a](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/d51e80a3011fd38012d3407f18439318deebd027))
* **fastani:** Add species rep information to heatmap. ([ed27df8](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/ed27df8c9a2b6f3a4cfe02e48510870e4dc2966a))
* **taxon:** Add option to limit get genomes by taxon to sp reps only. ([b61f749](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/b61f749736dbec113bfc0c5fa43a5afa35d48b1c))


### Reverts

* **fastani:** Testing the FastANI cmd output. ([7e597d1](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/7e597d107ced4aa4df9c36646a3f22b68483e310))

## [2.0.2](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.0.1...v2.0.2) (2022-05-06)


### Bug Fixes

* **fastani:** Remove grouping of qvr and rvq. ([0f601e2](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/0f601e283cc4a69579934f2fccef1661c0931b0d))

## [2.0.1](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.0.0...v2.0.1) (2022-05-03)


### Bug Fixes

* **genome:** Fixed an issue where genus type species may have been incorrect. ([b3a06c7](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/b3a06c76c519194e0bac644ac82fd23567cdbc85))

# [2.0.0](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v1.1.0...v2.0.0) (2022-04-08)


### Features

* **R207:** Updated for R207. ([727fde4](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/727fde489147461f8e2b736b2160822419147467))


### BREAKING CHANGES

* **R207:** Uses R207 database.

# [1.1.0](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v1.0.0...v1.1.0) (2022-03-11)


### Features

* **fastani:** Added cmd to FastAniResultData. ([3552864](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/35528644e9358dd321ca98f6ccef02c337002789))
* **meta:** Added GET meta/version to return the API version. ([86c19a4](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/86c19a49019b0466715ae25254ade1b6e3f19cd7))
* **meta:** Added GET meta/version to return the API version. ([d9cb6ed](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/d9cb6ed75fd01628db73f100872461883d042c2e))

# 1.0.0 (2022-03-04)


### Features

* **init:** Initial release. ([5eaeae3](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/commit/5eaeae3546240ca3c253806738f36ea57d556f9b))
