#!/bin/bash
echo "Test: Crawling https://www.google.com"
python fetch.py https://www.google.com
echo ""
echo "Test: Getting metadata from saved https://www.google.com link"
python fetch.py --metadata https://www.google.com
