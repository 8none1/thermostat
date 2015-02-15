#!/usr/bin/python
#
#  Get Met Office data
#
# Closest location is Sandy.  ID = 353363
#
# Look up from http://datapoint.metoffice.gov.uk/public/data/val/wxfcs/all/json/sitelist?key=71519fa6-3e60-42fa-af60-73565d1750af
#
#
#

import metoffer
api_key = "71519fa6-3e60-42fa-af60-73565d1750af"

M = metoffer.MetOffer(api_key)
x = M.nearest_loc_forecast(52.13224, -0.219987, metoffer.THREE_HOURLY)

print x

