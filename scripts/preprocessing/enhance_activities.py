import pandas as pd
import os

def enhance_activities():
    source_dir = 'data/source'
    activities_path = os.path.join(source_dir, 'activities.csv')
    
    if not os.path.exists(activities_path):
        print(f"Error: {activities_path} not found.")
        return
        
    df = pd.read_csv(activities_path)
    print(f"Loaded {len(df)} activities.")
    
    # Check if completed_at already exists
    if 'completed_at' not in df.columns:
        # Populate logically based on status
        # If status is Completed, use activity_date or updated_at, else None
        def get_completed_at(row):
            if row['status'] == 'Completed':
                # Use activity_date if available, else updated_at
                return row.get('activity_date', row.get('updated_at'))
            return None
            
        df['completed_at'] = df.apply(get_completed_at, axis=1)
        print("Added completed_at column.")
        
        # Save back to CSV
        df.to_csv(activities_path, index=False)
        print("Saved updated activities.csv.")
    else:
        print("completed_at already exists.")

    completed_count = df['completed_at'].notna().sum()
    non_completed_count = df['completed_at'].isna().sum()
    
    print(f"Total Activities: {len(df)}")
    print(f"Completed Activities: {completed_count}")
    print(f"Non-completed Activities: {non_completed_count}")

if __name__ == '__main__':
    enhance_activities()
