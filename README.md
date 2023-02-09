# Dashboard with Panama Maritime Efficiency and Sustainability indicators
[Dashboard](http://marpan.gabrielfuentes.org) with Panama Canal and Panama ports information

The database was generated from a [Panama Canal and Ports Algorithm](https://github.com/gabrielfuenmar/bunkering-recognition) that uses raw AIS information.

Dependencies:      
      
      pandas==1.3.3
      dash==2.8.1
      gunicorn==19.9.0
      geopandas==0.12.1
      scipy==1.9.3
      requests==2.27.1
      dash_auth==1.3.2
      geojson==2.5.0
      h3==3.7.4
      boto3==1.20.41


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
