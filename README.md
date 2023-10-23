# CharLib: An open-source standard cell library characterizer

- 🔩 Supports combinational and sequential cells
- 📈 Plots timing and I/O voltages
- 🧑‍💻 Easy-to-use, with YAML-based configuration
- 🐍 Implemented in Python 3 with a modified PySpice backend
- 🌶️ Compatible with ngspice and Xyce

## Introduction
CharLib is an open cell library characterizer originally based on [libretto](https://github.com/shiniziwa/libretto). The current version supports timing and power characterization of combinational and sequential cells.

## Installation
CharLib requires the following dependencies:

- [Python version 3.9 or newer](https://www.python.org)
- [Our modified version of PySpice](https://github.com/infinitymdm/PySpice)
- A compatible circuit simulator ([ngspice](https://ngspice.sourceforge.io/) or [xyce](https://xyce.sandia.gov/)).

Once the software listed above are installed, clone CharLib and try to run one of our test configurations:

```
$ git clone https://github.com/stineje/CharLib
$ cd CharLib
$ make gf180
```

A brief script will run to fetch the cell spice files, then you should see the software run characterization for several cells. If everything works as expected, CharLib will produce a liberty file called GF180.lib in the current directory.

## Usage
`./CharLib -l [DIR]`

CharLib searches the specified directory for a YAML file containing a valid cell library configuration, then characterizes the specified cells. See [yaml.md](https://github.com/stineje/CharLib/blob/main/docs/yaml.md) for information on constructing a config file.

The general process for using CharLib is as follows:
1. Acquire SPICE files for the cells you want to characterize
2. Write a configuration YAML file for the library
3. Run CharLib

## References
[1] M. Mellor and J. E. Stine, "CharLib: an open-source characterization tool written in Python", 2023. <br>
[2] Synopsys, "What is Library Characterization?", https://www.synopsys.com/glossary/what-is-library-characterization.html, 2023 <br>
[3] S. Nishizawa and T. Nakura, libretto: An Open Cell Timing Characterizer for Open Source VLSI Design, IEICE Transactions on Fundamentals of Electronics, Communications and Computer Sciences, 論文ID 2022VLP0007, [早期公開] 公開日 2022/09/13, Online ISSN 1745-1337, Print ISSN 0916-8508, https://doi.org/10.1587/transfun.2022VLP0007, https://www.jstage.jst.go.jp/article/transfun/advpub/0/advpub_2022VLP0007/_article/-char/ja, <br>
[4] I. K. Rachit and M. S. Bhat, "AutoLibGen: An open source tool for standard cell library characterization at 65nm technology," 2008 International Conference on Electronic Design, Penang, Malaysia, 2008, pp. 1-6, doi: 10.1109/ICED.2008.4786726. <br>
