import pandas as pd
import requests
from bs4 import BeautifulSoup
import json
import os
from dotenv import load_dotenv
from supabase import create_client, Client

class RedfinScraper:
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0'}

        # Initialize Supabase client
        load_dotenv()
        url: str = os.getenv("SUPABASE_URL")
        key: str = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL or SUPABASE_KEY is not set in the environment.")
        self.supabase: Client = create_client(url, key)

    def get_target_zips(self, state, zip_code=None):
        # Query the Supabase table for zip codes
        if zip_code is not None:
            return [zip_code]

        query = ( 
            self
            .supabase
            .schema('public')
            .table('ref_zipcode_mapping')
            .select('zip', 'state', 'primary_city')
        )

        if state is not None:
            # Filter by state
            response = query.eq('state', state).execute()
        else:
            # Filter by city and state
            return [zip_code]
        
        zips = [item['zip'] for item in response.data]
        return zips

    def get_stingray_rgn_id(self, zip_code):
        query_location_api = f"https://www.redfin.com/stingray/do/query-location?location={zip_code}&v=2"
        response = requests.get(query_location_api, headers=self.headers) 
        soup = BeautifulSoup(response.text, 'html.parser').text
        prefix_removed = soup.split('&&', 1)[1]
        data = json.loads(prefix_removed)
        try:
            region_id = data["payload"]["exactMatch"].get("id").split("_",1)[1]
            return region_id
        except:
            # print(f"No exact match found for zip code: {zip_code}")
            return None

    def build_stingray_gis_params(self, params):
        return "&".join(f"{key}={value}" for key, value in params.items() if value is not None)

    def get_api_url(self):
        raise NotImplementedError("Subclasses should implement this method")

    def call_api(self, params_url):
        api_url = self.get_api_url()
        url = f"{api_url}?{params_url}"
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.text, 'html.parser').text
        data = self.process_response(soup)
        return data

    def process_response(self, response_text):
        raise NotImplementedError("Subclasses should implement this method")
    
    def parse_data(self, data):
        raise NotImplementedError("Subclasses should implement this method")

    def scrape_zip(self, zip_code, params):
        region_id = self.get_stingray_rgn_id(zip_code)
        if region_id is None:
            return pd.DataFrame()
        params['region_id'] = region_id
        params_url = self.build_stingray_gis_params(params)
        data = self.call_api(params_url)
        parsed_data = self.parse_data(data)
        df = pd.DataFrame(parsed_data)
        return df

    def scrape_state(self, state, city=None, zip_code=None, limit=None):
        target_zips = self.get_target_zips(state, zip_code)
        total_zips = len(target_zips)
        if limit:
            target_zips = target_zips[:limit]
            total_zips = len(target_zips)  # Update total_zips if limit is applied

        print(f"Scraping {total_zips} Zip Codes in {state}")
        progress_updates = {
            25: int(0.25 * total_zips),
            50: int(0.50 * total_zips),
            75: int(0.75 * total_zips),
        }

        all_data = []
        for index, zip_code in enumerate(target_zips):
            if index + 1 in progress_updates.values():
                progress = (index + 1) / total_zips * 100
                print(f"Processing {int(progress)}% done ({index + 1}/{total_zips} zip codes)")

            df = self.scrape_zip(zip_code, self.get_default_params())
            if not df.empty:
                all_data.append(df)
        if all_data:
            final_df = pd.concat(all_data, ignore_index=True)
            return self.format_dataframe(final_df)
        else:
            return pd.DataFrame()

    def get_default_params(self):
        raise NotImplementedError("Subclasses should implement this method")

    def format_dataframe(self):
        raise NotImplementedError("Subclasses should implement this method")

class RentScraper(RedfinScraper):
    def get_api_url(self):
        return "https://www.redfin.com/stingray/api/v1/search/rentals"

    def process_response(self, response_text):
        # For rental listings, use the first part of the response
        json_data = response_text.strip()
        try:
            data = json.loads(json_data)
            return data
        except json.JSONDecodeError as e:
            print("Error decoding JSON:", e)
            print("Problematic response part:", json_data[:500])
            return {}

    def parse_data(self, data):
        homes = data.get('homes', [])
        parsed_homes = []
        
        for home in homes:
            home_data = home.get('homeData', {})
            rental_data = home.get('rentalExtension', {})
            
            home_info = {
                "property_id": home_data.get('propertyId'),
                "status": rental_data.get('status'),
                "price": rental_data.get('rentPriceRange', {}).get('max'),
                "square_feet": rental_data.get('sqftRange', {}).get('max'),
                "bedrooms": rental_data.get('bedRange', {}).get('max'),
                "bathrooms": rental_data.get('bathRange', {}).get('max'),
                "address": home_data.get('addressInfo', {}).get('formattedStreetLine'),
                "city": home_data.get('addressInfo', {}).get('city'),
                "state": home_data.get('addressInfo', {}).get('state'),
                "zip_code": home_data.get('addressInfo', {}).get('zip'),
                "url": home_data.get('url'),
                "latitude": home_data.get('addressInfo', {}).get('centroid', {}).get('centroid', {}).get('latitude'),
                "longitude": home_data.get('addressInfo', {}).get('centroid', {}).get('centroid', {}).get('longitude'),
                "description": rental_data.get('description'),
                "property_type": home_data.get('propertyType'),
                "country_code": home_data.get('addressInfo', {}).get('countryCode'),
                "rental_id": rental_data.get('rentalId'),
            }
            parsed_homes.append(home_info)
        
        return parsed_homes

    def get_default_params(self):
        params = {
            "al": 1,
            "isRentals": "true",
            "include_nearby_homes": "false",
            "num_homes": 350,
            "ord": "days-on-redfin-asc",
            "page_number": 1,
            "sf": "1,2,3,4,5,6,7",
            "status": 9,
            "uipt": "1,3,4",
            "v": 8,
            "region_type": 2,
            "region_id": None,
        }
        return params
    def format_dataframe(self, df):
        # Ensure all columns are in the correct format for RentScraper
        df['property_id'] = df['property_id'].astype(str)  # Assuming rental property IDs are strings
        df['status'] = df['status'].astype(pd.Int64Dtype())
        df['price'] = pd.to_numeric(df['price'], errors='coerce').astype(pd.Int64Dtype())
        df['square_feet'] = pd.to_numeric(df['square_feet'], errors='coerce').astype(float)
        df['bedrooms'] = pd.to_numeric(df['bedrooms'], errors='coerce').astype(float)
        df['bathrooms'] = pd.to_numeric(df['bathrooms'], errors='coerce').astype(float)
        df['address'] = df['address'].astype(str)
        df['city'] = df['city'].astype(str)
        df['state'] = df['state'].astype(str)
        df['zip_code'] = df['zip_code'].astype(str)
        df['url'] = df['url'].astype(str)
        df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce').astype(float)
        df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce').astype(float)
        df['description'] = df['description'].astype(str)
        df['property_type'] = df['property_type'].astype(pd.Int64Dtype())
        df['country_code'] = df['country_code'].astype(str)
        df['rental_id'] = df['rental_id'].astype(str)
        return df


class BuyScraper(RedfinScraper):
    def get_api_url(self):
        return "https://www.redfin.com/stingray/api/gis"

    def process_response(self, response_text):
        # Split the response on '&&' to separate different parts
        parts = response_text.split('&&')
        
        if len(parts) > 1:
            # The second part after '&&' is the one we need
            json_data = parts[1].strip()
            
            try:
                data = json.loads(json_data)
                return data
            except json.JSONDecodeError as e:
                print("Error decoding JSON:", e)
                print("Problematic response part:", json_data[:500])
                return {}
        else:
            print("Unexpected response structure. No valid JSON found.")
            return {}

    def parse_data(self, data):
        homes = data.get('payload', {}).get('homes', [])
        parsed_homes = []
        
        for home in homes:
            lat_long = home.get('latLong', {}).get('value', {})
            home_info = {
                "property_id": home.get('propertyId'),
                "listing_id": home.get('listingId'),
                "mls_id": home.get('mlsId', {}).get('value'),
                "status": home.get('mlsStatus'),
                "price": home.get('price', {}).get('value'),
                "hoa_fee": home.get('hoa', {}).get('value'),
                "square_feet": home.get('sqFt', {}).get('value'),
                "lot_size": home.get('lotSize', {}).get('value'),
                "bedrooms": home.get('beds'),
                "bathrooms": home.get('baths'),
                "location": home.get('location', {}).get('value'),
                "stories": home.get('stories'),
                "address": home.get('streetLine', {}).get('value'),
                "city": home.get('city'),
                "state": home.get('state'),
                "zip_code": home.get('postalCode', {}).get('value'),
                "year_built": home.get('yearBuilt', {}).get('value'),
                "url": home.get('url'),
                "latitude": lat_long.get('latitude'),
                "longitude": lat_long.get('longitude'),
                "description": home.get('listingRemarks'),
                "property_type": home.get('propertyType'),
                "country_code": home.get('countryCode'),
            }
            parsed_homes.append(home_info)
        
        return parsed_homes

    def get_default_params(self):
        params = {
            "al": 1,
            "include_nearby_homes": "false",
            "num_homes": 350,
            "ord": "days-on-redfin-asc",
            "page_number": 1,
            "sf": "1,2,3,4,5,6,7",
            "status": 9,
            "uipt": "1,3",
            "v": 8,
            "region_type": 2,
            "region_id": None,
        }
        return params
    
    def format_dataframe(self, df):
        # Ensure all columns are in the correct format for BuyScraper
        df['property_id'] = df['property_id'].astype(pd.Int64Dtype())
        df['listing_id'] = df['listing_id'].astype(pd.Int64Dtype())
        df['mls_id'] = df['mls_id'].astype(str)
        df['status'] = df['status'].astype(str)
        df['price'] = pd.to_numeric(df['price'], errors='coerce').astype(pd.Int64Dtype())
        df['hoa_fee'] = df['hoa_fee'].astype(str)
        df['square_feet'] = pd.to_numeric(df['square_feet'], errors='coerce').astype(float)
        df['lot_size'] = pd.to_numeric(df['lot_size'], errors='coerce').astype(float)
        df['bedrooms'] = pd.to_numeric(df['bedrooms'], errors='coerce').astype(float)
        df['bathrooms'] = pd.to_numeric(df['bathrooms'], errors='coerce').astype(float)
        df['location'] = df['location'].astype(str)
        df['stories'] = pd.to_numeric(df['stories'], errors='coerce').astype(float)
        df['address'] = df['address'].astype(str)
        df['city'] = df['city'].astype(str)
        df['state'] = df['state'].astype(str)
        df['zip_code'] = df['zip_code'].astype(str)
        df['year_built'] = pd.to_numeric(df['year_built'], errors='coerce').astype(float)
        df['url'] = df['url'].astype(str)
        df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce').astype(float)
        df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce').astype(float)
        df['description'] = df['description'].astype(str)
        df['property_type'] = df['property_type'].astype(pd.Int64Dtype())
        df['country_code'] = df['country_code'].astype(str)
        return df
