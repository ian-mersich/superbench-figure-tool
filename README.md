# Superbench Figure Tool

Create editable scientific figures and presentations. [Open the browser editor](https://imersich.com/superbench/figure_tool/).

This is 1.0.0-beta.19. The browser and Superbench packages use the same app, styles, vendors, 486 Library drawings (386 concepts), and 12 scientific scenes. SOURCE_RELEASE.json binds this export to their committed source and shared payload. Installed native-host qualification is separate.

Serve this directory over HTTP and open `web/`. Work stays in the current browser profile; download portable files for backups. First-party code is Apache-2.0 and original artwork is CC0-1.0. See LICENSE, NOTICE, LICENSE_POLICY.md, assets/LICENSE-ORIGINAL-ASSETS-CC0-1.0.md, assets/LICENSE-CELL-STRESS-TME-ANALYSIS-CC0-1.0.md and vendor/NOTICE.

The full release source ZIP includes verified preferred upstream sources under preferred-source-materials/. This slim Git export retains the same lock, complete notices, and fetch/verify instructions in vendor/SOURCE_MATERIALS.md. Fresh upstream compiler rebuilds are not qualified as byte-identical.

Run `python scripts/validate-scientific-assets.py --library --require-public-release`, `python scripts/validate-vendor-bundle.py`, and `python -m pytest tests/test_figure_tool_package_producer.py tests/test_scientific_product_release.py tests/test_export_figure_release_source.py tests/test_vendor_source_tools.py tests/test_vendor_fabric_portability.py`. See docs/UNIFIED_FIGURE_RELEASE.md for packaging and deployment.
