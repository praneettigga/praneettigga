<div align="center">

<img src="./assets/portrait.svg" width="470" alt="Animated ASCII portrait of Praneet Nischal Tigga" />

<img src="./assets/stats.svg" width="620" alt="GitHub contributions in the last year" />

[instagram](https://instagram.com/praneettigga) &nbsp;·&nbsp;
[linkedin](https://linkedin.com/in/praneet-nischal-tigga-613214324) &nbsp;·&nbsp;
[email](mailto:praneetnischal@karunya.edu.in)

</div>

<img src="./assets/heading-about.svg" width="620" alt="About" />

> Computer Science Engineering student building practical, full-stack products.<br>
> Interested in backend engineering, system design, Linux, and the details that make software dependable.

I am currently building **Travara** and learning Spring Boot, PostgreSQL, and backend engineering.<br>
Away from code, I have four years of experience producing music.

<img src="./assets/heading-stack.svg" width="620" alt="Stack" />

<samp>java &nbsp; javascript &nbsp; react &nbsp; node.js &nbsp; spring boot &nbsp; django &nbsp; postgres &nbsp; supabase &nbsp; docker &nbsp; linux</samp>

<img src="./assets/heading-featured.svg" width="620" alt="Featured" />

**[travara](https://github.com/praneettigga/travara)** &nbsp;·&nbsp; <samp>react, vite, nestjs, postgresql</samp><br>
A composable AI travel-planning workspace for building realistic itineraries around time,<br>
geography, budget, and the way people actually travel.

<img src="./assets/heading-stats.svg" width="620" alt="Stats" />

<div align="center">

<img src="./assets/streak.svg" width="620" alt="Current and longest contribution streaks" />

<img src="./assets/languages.svg" width="620" alt="Top languages across public repositories" />

<img src="./assets/year.svg" width="620" alt="A year of contributions represented as characters" />

</div>

<img src="./assets/heading-about-this-profile.svg" width="620" alt="About this profile" />

Every graphic in this README lives in this repository. The portrait is generated from a local<br>
photo with [`scripts/make_portrait.py`](./scripts/make_portrait.py); GitHub Actions redraws the<br>
statistics directly from GitHub once a day. The SVG animations use SMIL, so they work without<br>
JavaScript, external image services, or third-party uptime dependencies.

### Rebuilding the portrait

The original photograph is deliberately not committed. Install the one local dependency and run:

```bash
python3 -m pip install -r requirements-portrait.txt
python3 scripts/make_portrait.py /path/to/transparent-cutout.png \
  --crop 500,0,1550,1400 \
  --columns 90
```

Crop coordinates use source-image pixels. Transparent PNGs are composited onto white before
conversion, preserving their real cutout edge. For images without transparency, optional
`--mask-points` coordinates are normalized within the crop. Commit the resulting
`assets/portrait.svg`, not the private source photograph.

### Refreshing the statistics locally

```bash
GH_LOGIN=praneettigga python3 scripts/generate_stats.py
```

Without a token, the script bootstraps from GitHub's public profile and repository APIs. The
scheduled workflow uses its built-in `GITHUB_TOKEN` and GitHub's GraphQL API instead.
