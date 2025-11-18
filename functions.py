''' Functions '''

# Imports
import xarray as xr
import numpy as np


# Read data from file
def read_from_file(filepath='~/code/predictions/data/ERA5_T2m_1940-2025.nc'):
    return xr.open_dataset(filepath)


# Selects data subset for selected area (around Oslo) and time frame (1940-1969)
def get_data_subset(data,
    start_date = '1940-01-01',   # inclusive
    end_date   = '2025-07-31',   # inclusive
    lat_min    = 58,
    lat_max    = 63,    # north‑south limits
    lon_min    = 9,
    lon_max    = 13,    # west‑east limits
    ):
    return data.sel(time=slice(start_date, end_date), lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))


''' Returns xarray.Dataset with 
 - Dimensions: (dayofyear: 366)
 - Coordinates: dayofyear -> numbers from 1 to 366
 - Data variables: var167 -> expected temperature for each day of the year 
'''
def compute_climatology(data, start_date = '1940-01-01', end_date = '1969-12-31'):
    # Select data subset for computing reference climatology (and convert to °C)
    normal_subset = get_data_subset(data) - 273.15

    # Compute grid average temperature on each day
    # (spatial average temperature of the grid on each individual day between 1940 and 1969)
    daily_means = normal_subset.mean(dim=('lat', 'lon'))
    
    # Compute average temperature for each day of the year
    # (temporal average temperature, i.e. what to expect for Jan 03 each year)
    climatology = daily_means.groupby('time.dayofyear').mean('time')
    
    return climatology


# Yield (year, month) tuples from Jan start_year to Dec end_year inclusive.
def month_range(start_year: int, end_year: int, start_month=1, end_month=12):
    for yr in range(start_year, end_year + 1):
        for mo in range(start_month, end_month + 1):
            yield yr, mo


def count_hwd(data, climatology, start_year=1940, end_year=2024, start_month=1, end_month=12):
    hwd = []
    years = []

    for y in range(start_year, end_year+1):
        years.append(y)
        hwd_per_year = 0

        for m in range(start_month, end_month+1):

            # Select all data from selected year and month
            subset = data.sel(time=f'{y}-{m}')
            
            # Compute average temp in grid for each day of the selected time frame
            daily_grid_mean = subset.mean(dim=('lat', 'lon'))

            # Convert specific date into 'dayofyear' (necessary for anomaly calculation)
            daily_grid_mean_toy = daily_grid_mean.copy().groupby('time.dayofyear').mean('time')

            # Compute diffence between daily grid mean temp and expected temp
            difference = daily_grid_mean_toy-climatology

            # Select anomalies greater than +5°C
            above_thr = difference >= 5
            num_anomalies = above_thr['var167'].sum().item()
            hwd_per_year += num_anomalies

        hwd.append(hwd_per_year)

    hwd = np.array(hwd)
    years = np.array(years)
    return years, hwd


def seasonal_blocks(start_year,
                    end_year,
                    months):
    if not all(1 <= m <= 12 for m in months):
        raise ValueError("Months must be 1‑12")
    blocks = []
    for anchor in range(start_year, end_year):
        block = []
        for m in months:
            yr = anchor + (1 if m < months[0] else 0)
            block.append((yr, m))
        blocks.append(block)
    return blocks

# Calculates anomaly correlation coefficient
def ACC(Ok, Oavg, Yk, Yavg):
    Ydiff = Yk - Yavg
    Odiff = Ok - Oavg
    return sum(Ydiff*Odiff) / np.sqrt(sum(Ydiff**2) * sum(Odiff**2))

# Calculates root mean square error
def RMSE(O_k, Y_k):
    N = len(O_k)
    return np.sqrt(sum((Y_k - O_k)**2)/N)
    