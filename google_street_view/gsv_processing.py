#------------#
#-- author --#
#------------#
## Jason Schatz
## Created: 01.15.2017
## Last modified: 01.15.2017


#---------------#
#-- file info --#
#---------------#
## downloads google street view imagery for specified coordinates, angles, and views,
## classifies imagery as green vegetation, sky, or other, and calculates green view 
## index and percent visible sky for each location.


#----------------------#
#-- import libraries --#
#----------------------#
import glob
import numpy as np
import os
import pandas as pd
import scipy.misc
from scipy.misc import imread
import sys
import time
import urllib


#----------------------#
#-- define functions --#
#----------------------#
def get_GSV(locations, outpath):
  '''download GSV images for a set of locations, for all specified headings and pitches

    Args:
      locations: pandas df with SID, LAT, and LON columns (SID = sensorID)
      outpath: path for downloaded images
  '''
   for row in range(len(locations)):
      lat = locations.iloc[row]['LAT']
      lon = locations.iloc[row]['LON']
      sid = locations.iloc[row]['SID']

      for heading in headings:

         for pitch in pitches:
            temp_url = base_url + str(lat) + ',' + str(lon) + '&fov=60' + '&heading=' + str(heading) + '&pitch=' + str(pitch) + key
            filename = sid + '_' + str(heading) + '_' + str(pitch) + ".jpg"
            urllib.urlretrieve(temp_url, outpath + filename)

def percent_veg(r, g, b, pieces):
  '''calculate percent green canopy from GSV image using same rules as Li et al 2015:
    (1) product of green minus red and green minus blue is positive
    (2) green band is greater than the red band (in case both diffs are negative)

    Args:
      r: red band
      g: green band
      b: blue band

  '''
   diff = (g - r) * (g - b)
   mask1 = np.where(diff >= 0, diff, 0)
   mask2 = np.where(g > r, mask1, 0)
   green = np.where(mask2 > 0, 1, 0)
   # if pitch is 0 (horizontal), only use top half of image to calculate 
   # % green canopy; otherwise use entire image
   if pieces[2] == '0':
      top_half = green[0:(0.5 * np.shape(green)[0]), :]
      per_green = np.sum(top_half) / float((np.shape(top_half)[0] * np.shape(top_half)[1])) * 100
   else:
      per_green = np.sum(green) / float((np.shape(green)[0] * np.shape(green)[1])) * 100
   return per_green

def percent_sky(r, g, b, pieces):
  ''' calculate percent sky from GSV image. the classification rules are:
    (1) DN in blue band is >140
    (2) DN in blue band is greater than red DN minus 5 (blue is almost always
        much lower on other cover types, and in sky it is almost always > red)

    Args:
      r: red band
      g: green band
      b: blue band
      pieces: split strings of downloaded filename
  '''
   mask1 = np.where(b >= 140, 1, 0)
   mask2 = np.where(b >= (r - 5), 1, 0)
   sky = np.where((mask1 == 1) & (mask2 == 1), 1, 0)
   # if pitch is 0 (horizontal), only use top half of image to calculate 
   # % visible sky; otherwise use entire image
   if pieces[2] == '0':
      top_half = sky[0:(0.5 * np.shape(sky)[0]), :]
      per_sky = np.sum(top_half) / float((np.shape(top_half)[0] * np.shape(top_half)[1])) * 100
   else:
      per_sky = np.sum(sky) / float((np.shape(sky)[0] * np.shape(sky)[1])) * 100
   return per_sky


#-----------------------#
#-- define parameters --#
#-----------------------#
base_url = "https://maps.googleapis.com/maps/api/streetview?size=1200x800&location="
outpath = 'F:/Users/Jason/Desktop/UHI_GSV/Downloads/'
key = "&key=AIzaSyDAmTFEHOq8xxdXMJf4rla2_SspPVpxfYs"
headings = [0, 60, 120, 180, 240, 300]
pitches =  [-45, 0, 45, 90]
locations = pd.read_csv('F:/Users/Jason/Desktop/UHI_GSV/sensor_locations.csv')


#--------------------#
#-- acquire images --#
#--------------------#
get_GSV(locations=locations, 
        outpath=outpath)


#-------------------------------#
#-- calculate percent sky/veg --#
#-------------------------------#
start_time = time.clock()
## empty dictionary for results
results = {'SID': [],
           'heading': [],
           'pitch': [],
           'per_green': [],
           'per_sky': []
          }

## define globals
path1 = 'F:/Users/Jason/Desktop/UHI_GSV/Downloads'   # folder containing images
images_list = glob.glob(path1 + '/*.jpg')

## for each image in the folder...
for image_path in images_list:
  try:
    # read image
    img1 = imread(image_path).astype(float)

    # split filename into essential components (to extract pitch/heading/site name)
    pieces = image_path.split("//", 2)[-1]
    pieces = pieces.split("_", 3)
    pieces[2] = pieces[2].replace('.jpg', "")

    # define RGB bands
    r = img1[:, :, 0]
    g = img1[:, :, 1]
    b = img1[:, :, 2]

    # compute green veg mask
    per_green = percent_veg(r, g, b, pieces)

    # compute sky mask
    per_sky = percent_sky(r, g, b, pieces)

    # add results to dictionary
    results['SID'].append(pieces[0])
    results['heading'].append(pieces[1])
    results['pitch'].append(pieces[2])
    results['per_green'].append(per_green)
    results['per_sky'].append(per_sky)
  except:
    pass

## convert dictionary to dataframe and write to file
df1 = pd.DataFrame(results)
df1.to_csv(path1 + "/_raw_results.csv", index=False)
print(" %s seconds" % (time.clock() - start_time))


#-----------------------------------------------#
#-- aggregate data to get green view/sky view --#
#-- at each pitch                             --#
#-----------------------------------------------#
data = pd.read_csv(path1 + '/_raw_results.csv')

means = data.groupby(['SID', 'pitch']).agg(['mean'])
means.reset_index(inplace=True)
means.columns = ['SID', 'pitch', 'heading', 'per_green', 'per_sky']
means = means.drop('heading', 1)

means.to_csv(path1 + "/_means.csv", index=False)
