# Public release audit

Reviewed 2026-09-24. This is a scoped source-and-history review, not a guarantee that no sensitive information exists.

## Reviewed evidence

- Enumerated every tracked file in every reachable commit at review time (one initial commit).
- Scanned text for private-key headers, common provider token formats, quoted credential assignments, and absolute home-directory paths. No credential matches were found. A machine-specific README quickstart path required replacement before publication.
- Reviewed the README, project instructions, methodological limitations, and portfolio claims. The documented scope separates 384 local scripted episodes from 1,980 author-recorded episodes and leaves fresh model evaluation unverified.
- Verified that the reference repository uses the MIT license with Sierra's 2024 copyright notice. The public reanalysis includes extracted task reward labels; retain the source license notice with attribution alongside that derived artifact.
- Confirmed that raw upstream transcripts are not checked into this project. The reanalysis report contains task rewards, source URLs, source revision, and file hashes.
- Confirmed ignored credentials and environments (`.env`, `.env.*`, `.venv`) and ignored default live-run artifacts. A custom live-output filename can bypass that pattern; review new artifacts before committing them.

## Release conditions

Release preparation resolved these findings: the quickstart now uses git clone, LICENSE covers the independent code, and NOTICE preserves Sierra’s MIT attribution. The initial unpublished commit is replaced with the reviewed release tree, using a GitHub no-reply author address. Local tests passed. Workflow upload was rejected because the existing GitHub OAuth token lacks workflow scope; templates are included without claiming hosted CI execution. The static Pages site is published through the gh-pages branch.

Verify the public GitHub URL before deploying portfolio links. The portfolio copy describes an independent evaluation project and explicitly attributes archived model episodes to their authors. It makes no live-model, customer-impact, or production-deployment claim.

## Portfolio review

The homepage retains three main proof points and uses a short project mention; visible copy is 423 words after this update. The web resume adds 16 synthetic tasks, 384 scripted trials, and analysis of 1,980 published episodes. Its education remains in progress with Expected 2027, and its availability remains Available Full Time Now.

Publication does not replace future experimental validation. A fresh LLM study, held-out tasks, and independently checked model outputs remain separate work.
