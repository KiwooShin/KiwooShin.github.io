# Personal homepage

Single-file static site (`index.html`) — no framework, no build step.

## Edit

Everything lives in `index.html`: styles in the `<style>` block, content in the
`<main>` sections. Each project card has a commented-out snippet showing how to
swap the "coming soon" placeholder for a YouTube embed or a small local clip.
Put local media (small GIFs/MP4s, < ~10 MB each) in a `media/` folder; host
full-length demo videos on YouTube (unlisted is fine) and embed them.

## Deploy (GitHub Pages, free)

```bash
cd ~/work/homepage
git init && git add . && git commit -m "Initial homepage"
gh repo create KiwooShin.github.io --public --source=. --push
```

Then on GitHub: repo **Settings → Pages → Source: Deploy from a branch →
`main` / root**. The site appears at <https://kiwooshin.github.io> within a
minute or two. Any later `git push` updates it automatically.

(Naming the repo `KiwooShin.github.io` gives you the root URL; any other repo
name would serve at `kiwooshin.github.io/<repo>`.)
