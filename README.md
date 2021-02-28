# Spinorama : a library to display speaker frequency response and similar graphs
![image](https://github.com/pierreaubert/spinorama/workflows/Spinorama/badge.svg?branch=master)
[![DeepSource](https://deepsource.io/gh/pierreaubert/spinorama.svg/?label=active+issues&show_trend=true)](https://deepsource.io/gh/pierreaubert/spinorama/?ref=repository-badge)

This library provides an easy way to view, compare or analyse speakers data. This can help you take informed
decision when buying a speaker instead of relying on commercial information or internet buzz.

## Jump to the [gallery](https://pierreaubert.github.com/spinorama) of all (200+) speakers measurements.

# What is a spinorama set of graphs?

It is a way to understand quickly a speaker properties.

Here is an example:

![image](https://github.com/pierreaubert/spinorama/blob/develop/datas/pictures/ex-Genelec-8341A-cea2034.png)

- On Axis: this the frequency response. You expect it to be as flat as possible after 100Hz.
- Listening Window: an average of various measurements around on axis. Expected to be close to the previous one.
- Sound power DI: expected to be a smooth, slowy growing line.

The speaker above is *very* good.

Please read this [post](https://www.audiosciencereview.com/forum/index.php?threads/jbl-305p-mkii-and-control-1-pro-monitors-review.10811/) 
to get a better insight on how to analyse a spinorama.

# Features

## Import

The library support 4 kinds of data:
1. ASR format provided by a [Klippel NFS](https://www.klippel.de/products/rd-system/modules/nfs-near-field-scanner.html): a set of CSV files
2. Princeton 3D3A files: they are IR data in [hdf5](https://www.hdfgroup.org/solutions/hdf5/) format
3. Scanned data from a picture with [WebPlotDigitizer](https://automeris.io/WebPlotDigitizer/) (takes 10 minutes per picture)
4. Export in text form from [REW](https://www.roomeqwizard.com/)

## Computations

1. Generate CEA2034 data from horizontal and vertical SPL data
2. Calculate contour plot, radar plot, isolines and isobands.
3. Estimate basic data for a speaker (-3dB output, flatness over a range)
4. Compute various parameters defined in a paper from Olive (ref. below).
5. Can compute effect of an EQ (IIR) on the spinorama.
6. Generate an EQ to optimise the speaker (and get a better preference score) based on anechoic data. Note: this is not yet a room correction software.

## Generation

1. Webpages digestable on mobile but also on very large 4k screens
2. Graphs are interactive
3. Comparison between speakers
4. Some statistics


# Other ways to look at the graphs in a more interactive way.

## Linux or Mac user

First install a few packages:
```
apt install imagemagick npm
```
On a Mac you can replace all `apt` calls by `brew`.

### Using python3, ipython and Jupyter-Lab

```
pip3 install -r requirements.txt 
```
pip3 may also be pip depending on your system.

```
export PYTHONPATH=src
jupiter-lab &
```

Your browser will open, go to *experiments* directitory and click on *spinorama.ipynb* and play around.

## Linux or Mac developer

You are very welcome to submit pull requests. Note that the license is GPLv3.

Start with launching that should install a lot of software:
```
./setup.sh
```

If it doesn't work out of the box which is likely, please go step by step:

```
pip3 install -r requirements.txt 
pip3 install -r requirements-tests.txt 
```

For saving picture, you need a set of nodejs packages:
```
npm install vega-lite vega-cli canvas
```
and for linting the python, html and javascript code:
```
npm install pyright html-validator-cli standard
```
You may have to update your npm version above 12.0:
```
nvm install lts/fermium
```

Please add tests and
```
export PYTHONPATH=src
pytest --cov=src
```

Before committing, please check that the various checks are fine:

1. ```./check_html.sh``` : check that HTML generated files are conforming.
2. ```./check_meta.py``` : check that the metadata file looks sane.
3. ```flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exclude spinorama-venv``` should report 0
4. ```black .``` will take care of formatting all the python files.

and also (but WIP):
5. ```./check_404.sh``` : check we do not have missing links.
6. ```./node_modules/.bin/pyright````should not report new type error.
7. Check that notebook are cleaned up before committing.

Tests 1. to 4. should be in the presubmit.

# How to add a speaker to the database.

We have a dedicated [tutorial](./tutorial/ADDSPEAKER.md).

# Source of data and citations

## [AudioScienceReview *aka* ASR](https://www.audiosciencereview.com)
ASR is a fantastic source of speakers data thanks to [amirm@](https://www.audiosciencereview.com/forum/index.php?threads/a-bit-about-your-host.1906/). They also have a lot of data about DACs that you may found useful. There is little correlation between price and quality in the audio world and this data gives some objective criteria to decide what to buy.

## [3D3A](https://www.princeton.edu/3D3A/) is a research organisation at [Princeton](https://www.princeton.edu).

- They provide a database of speaker measurements ([manual](https://www.princeton.edu/3D3A/Manuals/3D3A_Directivity_Database.pdf))
- Some scientific papers I have used:
  - Metrics for Constant Directivity ([abstract](https://www.princeton.edu/3D3A/Publications/Sridhar_AES140_CDMetrics.html), [paper](https://www.princeton.edu/3D3A/Publications/Sridhar_AES140_CDMetrics.pdf), [poster](https://www.princeton.edu/3D3A/Publications/Sridhar_AES140_CDMetrics-poster.pdf))
    - Authors: Sridhar, R., Tylka, J. G., Choueiri, E. Y.
    - Publication: 140th Convention of the Audio Engineering Society (AES 140)
    - Date: May 26, 2016
  - A Database of Loudspeaker Polar Radiation Measurements ([abstract](https://www.princeton.edu/3D3A/Publications/Tylka_AES139_3D3ADirectivity.html), )
  - On the Calculation of Full and Partial Directivity Indices ([abstract](https://www.princeton.edu/3D3A/Publications/Tylka_3D3A_DICalculation.html))
    - Authors: Tylka, J. G., Choueiri, E. Y.
    - Publication: 3D3A Lab Technical Report #1
    - Date: November 16, 2014

## Books and research papers

- [Sound Reproduction: The Acoustics and Psychoacoustics of Loudspeakers and Rooms](https://books.google.ch/books/about/Sound_Reproduction.html?id=tJ0uDwAAQBAJ&printsec=frontcover&source=kp_read_button&redir_esc=y#v=onepage&q&f=false) By Floyd E. Toole
- Standard Method of Measurement for In-Home Loudspeakers is available for free at [CTA](https://www.cta.tech)
- A Multiple Regression Model for Predicting Loudspeaker Preference Using Objective Measurements: Part II - Development of the Model by Sean E. Olive, AES Fellow. Convention paper 6190 from the [AES](https://www.aes.org).
- Fast Template Matching. J.P.Lewis [pdf](http://scribblethink.org/Work/nvisionInterface/vi95_lewis.pdf)
- Farina, A. “Simultaneous Measurement of Impulse Response and Distortion with a Swept-Sine Technique,” Presented at the AES 108th Convention, Feb. 2000.
- Hatziantoniou, P. D. and Mourjopoulos, J. N. “Generalized Fractional-Octave Smoothing of Audio and Acoustic Responses,” J. Audio Eng. Soc., 48(4):259–280, 2000.

## Speakers manufacturers.

- If you are a manufacturer of speakers, it would be great if you could provide spinorama datas.
- Manufactures with good datas usually in speaker's manual:
  - JBL
  - Revel
  - Genelec
  - Adam
  - Eve Audio
  - Buscard Audio
  - KEF
  - JTR




