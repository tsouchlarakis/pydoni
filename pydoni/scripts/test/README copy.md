<div style="display: flex; justify-content: center;">
  <img src="img/back-up-icon.png" style="width: 300px; height: 300px;" />
</div>

# Back Up

> Fully back up a directory to another disk, scanning each file to determine whether to copy, replace or skip

---

```
Author           : Andoni Sooklaris  
Usage            : CLI
Input            : Folder containing files
Output           : Folder containing same files
Language(s)      : Python
Started Date     : 2019-01-04
Completed Date   : 2019-01-30
```

## Table of Contents

* [Description](#description)
* [Program Steps](#program_steps)
* [Setup](#setup)
* [Usage](#usage)
* [License](#license)


---

## Description
Back up a chosen folder to another location. Scan each file in the source and destination directories to determine if the source file has been modified more recently than the destination file. If so, replace destination file with source file. If not, skip source file. Check for any files in source that do not exist in destination and copy those as well. Check for any files in destination that do not exist in source and delete those.

The command line options `--skip_copy`, `--skip_replace` and/or `--skip_delete` may be added to the command line call to skip those elements of the program.

## Program Steps

##### 1. Scan Source and Destination Files

##### 2. Copy New Source Files to Destination
* Files that are in the source directory that do not exist in the destination

##### 3. Replace Existing Destination Files with Newer Source Files
* Files that have been modified in source

##### 4. Delete Destination Files Not in Source
* If files have been deleted from source, delete those from destination as well


## Dependencies
**Python Modules**

* 'os'
* 'sys'
* 'datetime'
* 'tqdm'
* 'shutil'
* 'time'
* 're'

## Usage
Any code that the user has to run goes here. This section should describe how to run the program.

```bash
python /Users/Andoni/GDrive/Programming/Git-Doni/photos/back-up/Back-Up.py "/path/to/source" "/path/to/destination"
```
---

## Changelog
### v1.0.0 - 2019-01-30

* Initial release!

## License

[![License](http://img.shields.io/:license-mit-blue.svg?style=flat-square)](http://badges.mit-license.org)

- **[MIT license](http://opensource.org/licenses/mit-license.php)**
- Copyright 2019 © **Andoni Sooklaris**
