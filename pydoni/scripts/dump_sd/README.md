<div style="display: flex; justify-content: center;">
  <img src="img/dump-sd-icon.png" style="width: 300px; height: 300px;" />
</div>

# Dump SD

> Extract photos and videos from a given date or set of dates from an SD card to an external hard drive.

---

```
Author           : Andoni Sooklaris  
Usage            : One-Click App
Input            : Media Files on SD Card
Output           : Files Moved to Disk
Language(s)      : Python
Started Date     : 2019-01-04
Completed Date   : 2019-01-10
```

## Table of Contents

* [Description](#description)
* [Program Steps](#program_steps)
* [Setup](#setup)
* [Usage](#usage)
* [License](#license)

---

## Description
This program accepts the following parameters in order to copy photo and video files from an SD card to an external hard drive:

* `Source Volume Name` - The name of the SD card.
* `Source Volume Type` - The format of the SD card.
* `Destination Volume Collection Path` - The absolute filepath of destination folder on external drive housing all photos from that event.

**NOTE**: The only option for `Source Volume Type` upon release is "Sony". This parameter refers to the file structure of the SD card, as different camera brands will format (arrange the file structure) differently.

These parameters will be prompted for in the Terminal upon program launch.

All files on the source volume (SD card) for a specified date (date range ok) will be copied to the destination collection if that file doesn't already exist. All output is logged to the console; this includes which files were copied and which were not copied, and any relevant explanations.

**NOTE**: This program may accept an optional `--today` flag when called on the command line. If specified, **it is assumed that the user would like to dump all photos from the current day to the most recent collection**. This will be verified before it is done. After photos are dumped, **the Rename and Convert DNG programs will be called automatically.**

## Program Steps

##### 1. Parse User Input
* Source Volume Name
* Source Volume Type
* Destination Volume Collection Path

#### 2. Scan Source Files
* Determine which dates have already been dumped by detecting which dates are already present in the metadata of files in 2019
* Prompt user to select date or date range of files to dump

##### 3. Copy Files
* Copy files from the source volume to the destination collection
* Photo files will be copied automatically to the "Photo" subdirectory (under the destination volume collection path)
* Video files will be copied automatically to the "Video" subdirectory
* Files will be renamed while they are copied

##### 4. Convert ARW to DNG
* Scan destination directory for `.arw` files
* If found, convert those `.arw` files to `.dng`

## Dependencies
**Python Modules**

* `os`
* `re`
* `sys`
* `tqdm`
* `click`
* `emoji`
* `shutil`
* `datetime`

## Usage
Any code that the user has to run goes here. This section should describe how to run the program.

```bash
open /Users/Andoni/GDrive/Programming/Git-Doni/photos/dump-sd/Run-Dump-SD.app
```
---

## Changelog

### v2.0.2 - 2019-03-28

* Added test mode for testing program
* Increased modularization in `main()`

### v2.0.1 - 2019-02-28

* Added support for DJI SD card

### v2.0.0 - 2019-02-24

* Combined Dump SD, Rename and Convert Raw programs into a single program!
* Added comprehensive check that files are not already dumped
* Inform user which dates have already been dumped when selecting dates from SD card
* Oriented largely towards custom Classes

### v1.0.0 - 2019-01-10

* Initial release!

## License

[![License](http://img.shields.io/:license-mit-blue.svg?style=flat-square)](http://badges.mit-license.org)

- **[MIT license](http://opensource.org/licenses/mit-license.php)**
- Copyright 2019 © **Andoni Sooklaris**
