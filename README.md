# HarvardX XML tools
## For dealing with edX courses

This is a bunch of batch tools to work directly with a course export (the file structure, not the tarball) or with .srt files. You can run `python3 filename.py` for each one to have it show a set of instructions, or just open the code with a text editor - the instructions are the first thing there.

Because python's built-in xml parser has trouble with namespaces and xpaths, some XML parsing is done with BeautifulSoup instead. It's included in this folder as `bs4`. BeautifulSoup requires `lxml` for XML parsing, so you'll need to install that, probably via `sudo pip3 install lxml`.

* `SetWeeksForAudit.py`, which sets the number of sections in the course (starting from the beginning) in which *all* graded problems will be available to audit learners.
* `SetMaxAttempts.py`, which sets the number of attempts automatically in every problem in a course.
* `SetShowAnswer.py`, which sets the showanswer value automatically (or removes it) in every problem in a course.
* `SetVideoDownloads.py`, which enables or disables video and/or transcript downloading for every video in a course.
* `SRTTimeShifter.py`, which moves the subtitles in an SRT file forward or backward a specified number of seconds.
* In the `outline_maker` folder there are a set of related items:
 * The `unicodecsv` package, which you should download and keep in the same folder with the python scripts.
 * Run `Make_Course_Outline.py` on your course export to create a TSV file with an outline of your course.
 * Open that in Google Docs and edit it to indicate which items are in which categories. Just mark the appropriate cells with an x.
 * Then save that as a new TSV file and run `Outline_to_HTML.py` on it to create a linked, filterable HTML outline that you can use as alternative navigation in your course.
 * Upload `hx-collapse-nav.js` and `hx-collapse-nav.css` to your Files & Uploads folder to complete the process.
 * If you want to show student scores next to each subsection, you should also upload `hx-grade-display.css` and `hx-grade-reader.js`, and add the following line of HTML (or something similar) near the top of your page: `<div id="progressbar">(Loading your scores <span class="fa fa-spinner fa-pulse fa-fw"></span>)</div>`

If you're looking for `Make_Course_Sheet`, `Make_Link_Spreadsheet`, and all their friends, that's in the hx_util repository as a package rather than a pile of scripts.

If you want `PrepAdaptiveProblems.py`, that's in the hx-adaptive repo.
