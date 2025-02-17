# CropInsuranceLoss
for downloading, reading, and extracting cause-of-loss data from USDA RMA records

## Getting Started

### Dependencies

Python Libraries:

* requests
* zipfile
* os
* io
* pandas
* numpy

### Executing program

* download zipped crop insurance data from www.rma.usda.gov by running
```
python -W ignore read_crop_loss_api.py
```
* this will download crop insurance loss data and unzip the files into 
* a subdirectory called 'crop_loss_data', with three sub-sub-directories: 'state_county_crop', 'type_practice_usage', 'cost_of_loss'
* create csv files with cause-of-loss, insured loss, insured value, and insured acreage data:
```
python -W ignore spark_analysis.py
```
* this will create loss data files for each individual state, as well as a nationwide loss data files
* new data is created in subdirectory 'crop_loss_data/readable_col_data_by_state'