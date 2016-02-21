---
layout: post
title: 3.0 Update Release Notes
date: 2016-02-16 20:00:00
---

Hi there guys, maybe you have already noticed, but the blog looks a bit different now, right? I have been thinking about redesigning the blog for a while now and last night I finally got right into building what I call the 3.0 version. So here are the release notes. I'm going to write about the changes I made this time and why I think they improve the overall experience, so if you're not interested in that you can stop right here.

Right when i started this project a couple of years ago I wanted to build a blog from the ground up, but at that time I didn't have the tools for it. You can't really build anything complex with just html and css, at least not efficiently. So instead of a blog I made a little site about me. I had some pages with a few photos, information about myself and my resume. 

For the second release I added a blog area using [Jekyll](http://jekyllrb.com) and kept the old pages. I needed a few subpages for the blog so therefore I added a second navigation bar under the background section. This looked alright esthetically I think, but it wasn't great conceptually. And now that I've lived with the 2.0 version for a while, I feel like the pages with the photos and the resume makes less and less sense.

The page with the resume was really annoying to maintain. Whenever I wanted to add something to my resume I had to add it to my pdf-resume, to [LinkedIn](http://se.linkedin.com/in/kimtorberntsson) and also to the homepage. It seemed like a lot of redundant extra work and therefore it made sense to remove it from the site. I have a link to my page on LinkedIn in the footer, so the info is still available, just in a better place.

Next I had a page with a couple of photos. The weird thing with that page was that you could not find any of the photos from the blog, so it was completely separated from that part of the page, which I think was both confusing and inelegant. So that made me think, maybe I could have a page that collects all of the photos from the blog. Well, that's exactly what I did. I call this page the [Gallery](/gallery), so if you want to look at the pictures this is where to go. You can get to the full posts from this view if you want to by clicking on the headers.

What's left after these changes is basically the blog. Since it is now (finally) clear that this is really a blog, it made sense to merge the blog navigation into the original navigation bar at the top. I think that all this makes much more sense than before, and that everything feels more consistent now.

While I was at it I decided to add some additional small artistic changes. First of all, I had this epiphany that maybe you could have the background from the latest post as background for the start page. In the end I decided that the pages that list a couple of posts per page (five in my case) should use the background image from their latest post. I think this was nice, because you can notice that the background changes as you browse through the pages. Also you can see whether or not you have read the latest post, since you'll notice a new background if you have not. 

As a final touch I worked a bit more with the colors of the site. Generally I'm careful with the coloring, since I want to keep things clean and simple. I also have lots of photos with varying color schemes in them, meaning that it's practically impossible to use colors that work with every possible photo. That said, I used quite a lot of orange when you hovered around the site with your mouse, but if you've been browsing on a phone, you might not have noticed this at all.

I like the orange highlighting, but I wanted to take things one step further, so I decided that every page should have it's own color scheme. The arrows, links and headers all use the color theme of it's own page. I think of it as playful without being too childish, but I guess that a few of you might disagree about that. Anyway, now the [Gallery](/gallery), [Archive](/archive), [Blog](/) and the [About](/about) pages all have their distinctive color schemes. The icons of the footer also have some new coloring when you hover over them.

I've actually changed a couple of things under the hood as well, but I think I will write something short (hopefully) about that further along. Thanks for bearing with me. Next post will probably be about Monster Trucks, so stay tuned. 
