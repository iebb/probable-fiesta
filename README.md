## probable-fiesta

A simple single-page web crawler for ???.

It crawls:
* The web page itself
* Any \<script src\> scripts 
* Any \<img src=""\> or \<img srcset=""\> images
* Any \<link rel="stylesheet"\> external stylesheets
* Inside external stylesheets and \<style\> tags:
  * Absolute URLs inside stylesheets inside url(https?://)
  * Relative and Absolute URL references inside url()

It modifies:
* removes crossorigin tags so it works locally
* filenames of resources into locally-stored filenames
* adds some metadata inside the saved html file

Limitations:
* Javascript isn't executed, so resources referenced from JS aren't downloaded.