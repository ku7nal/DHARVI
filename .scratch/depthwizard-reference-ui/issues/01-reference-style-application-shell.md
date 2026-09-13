# 01 — Reference-style application shell and navbar

**What to build:** Replace the existing workspace shell with a clean reference-inspired product surface: centered dark rounded navbar, DepthWizard branding, reference-style navigation labels, pale neutral canvas, editorial typography, violet accents, and a polished default reconstruction state.

**Blocked by:** None — can start immediately.

**Status:** resolved

- [x] The app opens with a centered dark rounded navbar containing DepthWizard branding, Home, Products, Industries, Company, Resources, and a violet `New reconstruction →` CTA.
- [x] The CTA activates or focuses the primary reconstruction/upload workflow.
- [x] The default screen uses the reference-inspired neutral background, black typography, violet gradient accents, rounded controls, restrained borders, and generous spacing.
- [x] The existing navigation remains usable while adopting the new visual presentation.
- [x] The empty reconstruction state presents a clear product headline, supporting copy, upload action, supported-format hint, and GAMUS example action.
- [x] The shell remains usable on desktop, tablet, and mobile widths.

## Implementation notes

The shell uses inline SVG/CSS for the reference-inspired connector network so it does not add an image-asset dependency. Existing prediction and benchmark behavior remains behind the redesigned shell.
