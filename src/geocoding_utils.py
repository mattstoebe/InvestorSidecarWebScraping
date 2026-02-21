import geopandas as gpd


class Geocoder:
    def __init__(   self, 
                    df, 
                    latitude_col='latitude', 
                    longitude_col='longitude', 
                    demographic_areas_path=None,
                    cbsa_source_path=None, 
                    state_source_path=None
                    ):
        
        self.df = df
        self.latitude_col = latitude_col
        self.longitude_col = longitude_col
        
        # Set default paths
        self.demographic_areas_path = demographic_areas_path
        self.cbsa_source_path = cbsa_source_path
        self.state_source_path = state_source_path
        
        # Convert the DataFrame to a GeoDataFrame
        self.gdf = gpd.GeoDataFrame(
            self.df, 
            geometry=gpd.points_from_xy(self.df[self.longitude_col], self.df[self.latitude_col]), 
            crs="EPSG:4326"
        )

    def geocode_demographics(self, demographic_areas_path):
        # Load and preprocess demographic areas
        demographic_areas = gpd.read_file(demographic_areas_path)
        demographic_areas.to_crs("EPSG:4326", inplace=True)
        demographic_areas["GEOID"] = demographic_areas["FIPS"]
        demographic_areas = demographic_areas[["GEOID", "geometry"]].rename(columns={"GEOID": "cbg_geoid"})
        
        # Perform spatial join with demographic areas
        geocoded_gdf = self.gdf.sjoin(demographic_areas, how="left").drop(["index_right"], axis=1)
        return geocoded_gdf.drop(['geometry'], axis=1)

    def geocode_cbsa(self, cbsa_source_path):
        # Load and preprocess CBSA areas
        cbsa_source = gpd.read_file(cbsa_source_path)
        cbsa_source.to_crs("EPSG:4326", inplace=True)
        cbsa_source = cbsa_source[["GEOID", "NAME", "geometry"]].rename(columns={"GEOID": "cbsa_geoid", "NAME": "cbsa_name"})
        
        # Perform spatial join with CBSA areas
        geocoded_gdf = self.gdf.sjoin(cbsa_source, how='left').drop(["index_right"], axis=1)
        return geocoded_gdf.drop(['geometry'], axis=1)

    def geocode_state(self, state_source_path):
        # Load and preprocess state areas
        state_source = gpd.read_file(state_source_path)
        state_source.to_crs("EPSG:4326", inplace=True)
        state_source = state_source[["FID", "State_Code", "geometry"]].rename(columns={"FID": "state_id", "State_Code": "state_code"})
        
        # Perform spatial join with state areas
        geocoded_gdf = self.gdf.sjoin(state_source, how='left').drop(["index_right"], axis=1)
        return geocoded_gdf.drop(['geometry'], axis=1)

    def geocode_all(self, demographic_areas_path=None, cbsa_source_path=None, state_source_path=None):
        # Geocode using demographic areas
        geocoded_gdf = self.geocode_demographics(demographic_areas_path)
        
        # Update the GeoDataFrame with the results
        self.gdf = gpd.GeoDataFrame(
            geocoded_gdf, 
            geometry=gpd.points_from_xy(geocoded_gdf[self.longitude_col], geocoded_gdf[self.latitude_col]), 
            crs="EPSG:4326"
        )

        # Geocode using CBSA areas
        geocoded_gdf = self.geocode_cbsa(cbsa_source_path)
        
        # Update the GeoDataFrame with the results
        self.gdf = gpd.GeoDataFrame(
            geocoded_gdf, 
            geometry=gpd.points_from_xy(geocoded_gdf[self.longitude_col], geocoded_gdf[self.latitude_col]), 
            crs="EPSG:4326"
        )

        # Geocode using state areas
        geocoded_gdf = self.geocode_state(state_source_path)
        
        # Return the final DataFrame after all geocoding steps
        return geocoded_gdf