---
layout: post
title: Sublime Setup for LaTeX
date: 2015-11-01 20:56:00
background: latex
---

First of, wasn't that a really amazing title for a blog post? Those of you who get it will get it I think.

With [El Cap](https://en.wikipedia.org/wiki/OS_X_El_Capitan) of course [MacTex](https://tug.org/mactex/) ran into some problems. I remember having issues with [Yosemite](https://en.wikipedia.org/wiki/OS_X_Yosemite) as well. Luckily they were not too difficult to [fix](https://tug.org/mactex/elcapitan.html). So while I was at it I decided to take a look at my setup for [LaTeX](https://www.latex-project.org) editing.

First of all I decided that it was time to upgrade from [Sublime Text 2](http://www.sublimetext.com/2) to [Sublime Text 3](http://www.sublimetext.com/3). The third version is still in beta, but should be a bit faster due to it being written in [Python 3](https://www.python.org/download/releases/3.0/) (not that Sublime Text 2 ever was slow) and pretty stable by now. The reason why I use Sublime instead of one of the applications that are provided with the LaTeX distribution is simply because they all suck. They look gross, have terrible syntax highlighting and lack important text editing capabilities that Sublime provides, like auto completion and multiple cursor selections. Actually, the first thing I do when I install MacTex is always to delete all of these applications, since they are a disgrace to my operating system and should not be allowed to live within my computer.

!["LaTeX Logo"](/assets/pictures/latex.svg)

For those of you who still use one of these terrible applications, here is a guide to set up the environment I use. It's actually really, really easy. I did it on OSX, but it should be very similar on Windows or Linux. [Skim](http://skim-app.sourceforge.net) will not be available, but there are some alternatives to it if you google around. Just follow these steps:

* Install a LaTeX distribution
* Install Sublime Text
* Install Package Control for Sublime Text using this [guide](https://packagecontrol.io/installation). You just paste some code they provide into Sublime's command line and restart Sublime.
* Install [LaTeXing](http://www.latexing.com) using Package Control. You do that by pressing cmd+shift+p and then write *Package Control: Install Package*. Press enter and then write *LaTeXing*. Press enter again and restart sublime.
* Install [LaTeX-cwl](https://packagecontrol.io/packages/LaTeX-cwl) using package control in the same way you installed LaTeXing before. This is what will give you auto-completion in Sublime.
* Install Skim if you're on OSX. It is used to view the pdf files. 

Now everything is set up. If you save a file in the .tex-format the highlighting and auto-completion should be in place. To build a LaTeX document from within Sublime just press cmd+b. A pdf will be created and opened in Skim.

!["Sublime Text Logo"](/assets/pictures/sublime.png)

The most popular LaTeX package for Sublime is most likely [LaTeXTools](https://github.com/SublimeText/LaTeXTools), but now that I have tested both I really prefer LaTeXing. It provides auto completion with the LaTeX-cwl package, which is amazing to have. I also find that the compiler messages looks a bit better.

Lastly I want to mention two small cosmetic changes I did to Sublime Text. The app icon looks alright, but I do think it should be simpler and probably round. I searched a bit and found a really [nice icon](https://dribbble.com/shots/1705218-Sublime-Text-Yosemite-Icon) I replaced the default one with. It's actually very easy to chance icons in OSX. You just right click on the app in finder and choose *Get Info*. Then you drag and drop the new icon to the old icon located at the top left of the information window.

When I dragged a folder onto Sublime Text 3 I found something really horrific (worse than anything I saw this Halloween). In addition to these really nice arrows that indicate folders, they have added extremely ugly icons for different files and folders. These were so terrible that I would have to downgrade to Sublime Text 2 if there was no way of getting rid of them. Luckily (as so many times before) the day was saved by [Stack Overflow](http://stackoverflow.com/questions/25487263/hide-icons-in-sidebar). Basically you have to replace the code concerning the folder and file icons in the default theme for the icons with the following:

{% highlight css %}
{
    "class": "icon_file_type",
    "content_margin": [0,0]
},
{
    "class": "icon_folder",
    "content_margin": [0,0]
},
{
    "class": "icon_folder_loading",
    "content_margin": [0,0]
}
{% endhighlight %}

Hope someone found this helpful. This is the best way to write LaTeX that I have seen, with the possible exception of just writing everything online using [Overleaf](https://www.overleaf.com/?utm_expid=71700200-3.zinQGCQWTZa5ZTVcJEdM-w.0#.VjZnaIS9gS0). I still think that Sublime provides a better text editor, and somehow it feels a bit better to have the files in a [Dropbox](https://www.dropbox.com) folder. It is easier to get started with Overleaf though.