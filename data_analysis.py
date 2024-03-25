import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.sql import text

# Engines for BigQuery and Redshift
engine_bq = create_engine('bigquery://project/dataset')
engine_rs = create_engine('redshift+psycopg2://user:password@host:port/database')

def load_data_from_vault(table_name, engine, columns=None, filters=None):
    """Generic function to load data from a table with optional columns and filters."""
    base_query = f"SELECT {','.join(columns) if columns else '*'} FROM {table_name}"
    if filters:
        conditions = ' AND '.join(f"{col} = '{val}'" for col, val in filters.items())
        query = f"{base_query} WHERE {conditions}"
    else:
        query = base_query
    return pd.read_sql(text(query), engine)

def analyze_user_behavior():
    """Analyze user behavior using data from Hub, Link, and Satellite structures."""
    try:
        # Load user interactions (Satellite) from BigQuery
        interactions_df = load_data_from_vault(
            'satellite_user_interactions',
            engine_bq,
            columns=['user_hashkey', 'interaction_type', 'interaction_time']
        )

        # Load content metadata (Hub) from Redshift
        content_metadata_df = load_data_from_vault(
            'hub_content_metadata',
            engine_rs,
            columns=['content_hashkey', 'title', 'category']
        )

        # Load user-content interactions (Link) from BigQuery
        user_content_interactions_df = load_data_from_vault(
            'link_user_content_interactions',
            engine_bq,
            columns=['user_hashkey', 'content_hashkey', 'interaction_time']
        )

        # Perform analysis
        # Example1: Count interactions by user
        user_interaction_counts = interactions_df.groupby('user_hashkey').size().reset_index(name='interaction_count')

        # Example2: Most popular content categories
        content_category_counts = content_metadata_df['category'].value_counts()

        # Example3: User-content interaction matrix
        user_content_matrix = user_content_interactions_df.pivot_table(
            index='user_hashkey',
            columns='content_hashkey',
            values='interaction_time',
            aggfunc='count',
            fill_value=0
        )

        # Save analysis results
        user_interaction_counts.to_csv('user_interaction_counts.csv', index=False)
        content_category_counts.to_csv('content_category_counts.csv', header=['category', 'count'])
        user_content_matrix.to_csv('user_content_matrix.csv')

        print("Data analysis completed successfully.")

    except Exception as e:
        print(f"An error occurred during data analysis: {str(e)}")

# Main execution
if __name__ == "__main__":
    analyze_user_behavior()
