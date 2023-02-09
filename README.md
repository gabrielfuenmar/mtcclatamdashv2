# Dashboard with Panama Maritime Efficiency and Sustainability indicators
[Dashboard](http://marpan.gabrielfuentes.org) with Panama Canal and Panama ports information

The database was generated from a [Panama Canal and Ports Algorithm](https://github.com/gabrielfuenmar/bunkering-recognition) that uses raw AIS information.

Dependencies:      
      
      pandas==1.1.4
      dash==1.17.0
      gunicorn==19.9.0
      geopandas==0.8.1
      scipi==1.4.1
      requests==2.23.0
      dash_auth==1.3.2
      geojson==2.5.0
      h3==3.7.3

Parameters: 

      draught_restr_data: dataframe with historical draught restrictions and gatun_lake levels
      emissions.csv: ships emissions for 2018 at Panama Area
      panama_transits_sp: Panama Canal transit information as generated by Panama Canal algorithm
      ports_solutions_sp: Panama ports information as generated by ML algorithm
      Panama_Ports.geojson: Polygons file for Panama ports

Returns: 

      Dashboard deployed in panmaritime.gabrielfuentes.org or stats.mtcclatinamerica.com via Heroku
        
Code development:
  
        1.Def functions built for every container and linked via a bigger div.html
        2.Particulars of every container retrieved from style.css
        3.Callbacks assigned to every relevant container from every input and map
 

https://user-images.githubusercontent.com/45942967/117957191-18b57980-b31a-11eb-8e65-a7707f625c77.mp4


Credits: Gabriel Fuentes Lezcano

Licence: MIT License

Copyright (c) 2020 Gabriel Fuentes

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
© 2019 GitHub, Inc.
