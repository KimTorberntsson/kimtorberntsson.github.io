---
layout: post
title: This Blog is Built Using Jekyll
date: 2015-09-06 10:50:00
background: jekyll
---

Ok so this might get a bit technical.

Once I finished [kimtorberntsson.com](http://kimtorberntsson.com) 1.0 I gave up on implementing a blog there for some time. I kept my tumblr (which I rarely used at all) for the time being and moved on with life. Then I listened to an [episode](http://kodsnack.se/58/) of the excellent Swedish programming podcast [Kodsnack](http://kodsnack.se), where they discussed (among other interesting topics) something called static html generators. They had used it to build their site quickly and once I had heard the idea behind these generators, I became interested in using one too. Apparently [Jekyll](http://jekyllrb.com) is the most commonly used generator. And this is cool: [GitHub](http://github.com) has a project called [GitHub Pages](https://pages.github.com), where they host sites for you for free and ... wait for it ... they support Jekyll.

![Jekyll logo](/assets/pictures/jekyll.png)

So what is this about really? Well, the terrible, terrible thing with writing html is that it is markup and not programming, meaning that you write *exactly* what should be displayed. This sound reasonable, but often times you want to include similar content in several places and then you can quickly find yourself in copy hell. It gets even worse when you have several pages sharing for example a navigation panel. Since you are just copying all the time, when you find yourself wanting to add something you will have to add it in several places. Or rather, you pull your hair out, get depressed, give up and in the end keep the site as it was. 

The cool thing with Jekyll is that you use some smart tools for generating the page. You can include often used html sections where you want to. You have access to for loops, if statements and similar basic programming stuff. And this actually makes all the difference, since you can easily get a setup where you only have to change your code in one place, should you want to implement something new. It gets even better, since you can actually get away from writing html at all. With Jekyll you can write your posts and pages in [markdown](https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet), a really nice format for annotations originally invented by [John Gruber](http://daringfireball.net/projects/markdown/). Remember when I complained about having to write posts within html tags? Well, that's not happening now that I use Jekyll.

![Github Pages](/assets/pictures/github.png)

And it gets even better. Like I mentioned before, GitHub Pages lets you host your site at them for free, but there is actually more to it than that. You don't actually host your html-generated site there, instead you host your Jekyll *project*. And when you commit changes your site is rebuilt automatically. This means that all I have to do in order to add a new blog post is to write it in markdown in my favourite editor and then just push the changes to GitHub. This is just as easy (if not easier) than writing a blog post in [tumblr](https://www.tumblr.com) or [WordPress](https://wordpress.org), but way, way cooler and more hacksy. And since the project is hosted on Github everyone who is interested can look at my [source code](https://github.com/KimTorberntsson/kimtorberntsson.github.io) and use it for inspiration.

![Daring Fireball](/assets/pictures/daring-fireball.png)

There are also some nice aspects with using a generator instead of for example a database, which could of course do the same thing and much more. Jekyll can be seen as a factory that creates static pages. That means that there will be no database calls or scripts for changing the [DOM](https://en.wikipedia.org/wiki/Document_Object_Model), it's all just static pages. This means that it's easy to understand the html and the page will load very fast. Of course there's lots of things you can't do with a static site, but in my case this was a perfect fit. Hope this makes sense and that you also get excited, because Jekyll is really nice.

And here are a few links I took inspiration from when building this blog:

* [Jekyll Homepage](http://jekyllrb.com/)
* [Codecourse's video guide](https://www.youtube.com/watch?v=iWowJBRMtpc)
* [Joshua Lande's blog](http://joshualande.com/jekyll-github-pages-poole/)
* [Joel Glovier's blog](http://joelglovier.com/writing/rss-for-jekyll/ )
* [Github Pages](https://pages.github.com/)
* [Smashing Magazine's guide](http://www.smashingmagazine.com/2014/08/build-blog-jekyll-github-pages/)
* [David Ensinger about Github Pages and DNS](http://davidensinger.com/2013/03/setting-the-dns-for-github-pages-on-namecheap/)