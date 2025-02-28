# HarvardX XML tools
## For dealing with edX courses

This is a bunch of batch tools to work directly with a course export (the file structure, not the tarball) or with .srt files. You can run `python3 filename.py` for each one to have it show a set of instructions, or just open the code with a text editor - the instructions are the first thing there.

## Setup

I recommend using a virutal environment to install the requirements:

```bash
> python3 -m venv hxxml_venv
> source hxxml_venv/bin/activate
> pip3 install \(package names\)
```

If you want to install the required packages for all scripts, you will need:

* `lxml`
* `tinycss2`
* `bs4` (which is BeautifulSoup)
* `chardet`
* `markdownify`

The most recent versions should work. Several of them are included in this repo already, with versions that I know work. If you have difficulty some day in the future, give these a shot.

## The Tools

* `SortStaticFiles.py` finds any files in the /static/ folder that aren't in use and cordons them off into an "unused" folder.
* `NameThatPage.py` adds an XML comment in every chapter, sequential, and vertical file to indicate its location in the course.
* `md2edx.py` and `edx2md.py` are intended to help with transcription. Run one to take the files from the HTML folder and turn them into markdown files. Run the other on markdown files to make HTML.
* `WordCount.py` is a transcription planning tool. It attempts to give a reasonable word count for the entire course. Must be run after `edx2html`. Not a really carefully-polished script.
* `YouTube_Remediation.py` takes all the videos in a course and strips out the YouTube URL, forcing them to rely on the other listed source. It only does that if there _is_ another listed source. It also reports iframes and links to YouTube for further investigation.
* `MakeNewRun.py`, which _does_ work directly on the course tarball. It extracts the course, gets a bunch of info, adjusts the run number, saves the info to a file, and rezips the course for upload to a new shell.
* `SetMaxAttempts.py`, which sets the number of attempts automatically in every problem in a course.
    * `SetMaxAttemptsIfGraded.py`, just like the last one but only works on problems with a non-zero weight.
* `SetShowAnswer.py`, which sets the showanswer value automatically (or removes it) in every problem in a course.
    * `SetShowAnswerIfGraded.py`, just like the last one but only works on problems with a non-zero weight.
* `SetVideoDownloads.py`, which enables or disables video and/or transcript downloading for every video in a course.
* `SRTTimeShifter.py`, which moves the subtitles in an SRT file forward or backward a specified number of seconds.
* In the `outline_maker` folder there are a set of related items:
    * The `unicodecsv` package, which you should download and keep in the same folder with the python scripts.
    * Run `Make_Course_Outline.py` on your course export to create a TSV file with an outline of your course.
    * Open that in Google Docs and edit it to indicate which items are in which categories. Just mark the appropriate cells with an x.
    * Then save that as a new TSV file and run `Outline_to_HTML.py` on it to create a linked, filterable HTML outline that you can use as alternative navigation in your course.
    * Upload `hx-collapse-nav.js` and `hx-collapse-nav.css` to your Files & Uploads folder to complete the process.
    * If you want to show student scores next to each subsection, you should also upload `hx-grade-display.css` and `hx-grade-reader.js`, and add the following line of HTML (or something similar) near the top of your page: `<div id="progressbar">(Loading your scores <span class="fa fa-spinner fa-pulse fa-fw"></span>)</div>`

If you're looking for `Make_Course_Sheet`, `Make_Link_Spreadsheet`, and all their friends, that's in the [hx_util](https://github.com/Colin-Fredericks/hx_util) repository as a package rather than a pile of scripts.
