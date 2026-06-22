# App photos

Drop licensed photos here with these exact filenames (referenced from
`src/data/trails.ts` and the screens). Until a file exists, the UI shows a
tasteful palette placeholder in its place — nothing breaks.

| File | Used by |
|------|---------|
| `raptor-ridge.jpg` | Discover hero background + Trail Detail hero |
| `avatar.jpg` | Profile (You) avatar |
| `barred-owl.jpg` | Targeting species card |
| `pileated-woodpecker.jpg` | Targeting species card + Bird ID result |
| `red-fox.jpg` | Targeting species card |
| `northern-goshawk.jpg` | Targeting species card |
| `viewfinder.jpg` | Bird ID camera background |

Recommended: landscape ~1200×800 for `raptor-ridge.jpg` / `viewfinder.jpg`,
square for the avatar and species thumbnails. Anything in `public/` is served
from the site root, so `raptor-ridge.jpg` resolves to `/assets/raptor-ridge.jpg`.
