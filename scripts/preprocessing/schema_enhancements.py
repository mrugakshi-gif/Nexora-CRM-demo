import pandas as pd
import os
import shutil
import uuid

def enhance_schema():
    source_dir = 'data/source'
    backup_dir = 'data/source_backup'
    
    # 1. Backup original data
    print("Backing up source data...")
    if os.path.exists(backup_dir):
        shutil.rmtree(backup_dir)
    shutil.copytree(source_dir, backup_dir)
    print(f"Backup created at {backup_dir}")
    
    # 2. Create users.csv based on sales_reps
    print("Creating users.csv...")
    reps_df = pd.read_csv(os.path.join(source_dir, 'sales_reps.csv'))
    
    # Generate user IDs mapped to rep IDs
    users_data = []
    for _, rep in reps_df.iterrows():
        # A simple deterministic hash or just UUID for user_id
        user_id = f"USR-{rep['rep_id'].split('-')[-1]}"
        users_data.append({
            'user_id': user_id,
            'rep_id': rep['rep_id'],
            'email': rep['email'],
            'password_hash': 'hashed_placeholder_123!@#',
            'role': 'Admin' if rep['role'] == 'Sales Director' else 'User',
            'is_active': rep['is_active'],
            'created_at': rep['hire_date'],
            'updated_at': rep['hire_date'],
            'deleted_at': None
        })
    
    # Add a system admin user for generic "created_by" where rep is unknown
    users_data.append({
        'user_id': 'USR-SYSTEM',
        'rep_id': None,
        'email': 'admin@system.local',
        'password_hash': 'hashed_placeholder_sys',
        'role': 'System Admin',
        'is_active': True,
        'created_at': '2022-01-01',
        'updated_at': '2022-01-01',
        'deleted_at': None
    })
    
    users_df = pd.DataFrame(users_data)
    users_df.to_csv(os.path.join(source_dir, 'users.csv'), index=False)
    print(f"Created users.csv with {len(users_df)} records.")
    
    # Map reps to user_ids for assigning created_by / updated_by
    rep_to_user = {row['rep_id']: row['user_id'] for row in users_data if row['rep_id'] is not None}
    
    # 3. Enhance core tables
    core_tables = [
        'companies.csv', 'contacts.csv', 'leads.csv', 'opportunities.csv', 
        'activities.csv', 'customers.csv', 'customer_transactions.csv', 
        'customer_support_cases.csv', 'products.csv', 'campaigns.csv'
    ]
    
    for table in core_tables:
        path = os.path.join(source_dir, table)
        if not os.path.exists(path):
            continue
            
        print(f"Enhancing {table}...")
        df = pd.read_csv(path)
        
        # Determine logical owner/creator
        created_by_col = None
        if 'assigned_rep_id' in df.columns:
            created_by_col = 'assigned_rep_id'
        elif 'owner_rep_id' in df.columns:
            created_by_col = 'owner_rep_id'
        elif 'account_owner_rep_id' in df.columns:
            created_by_col = 'account_owner_rep_id'
        elif 'sales_rep_id' in df.columns:
            created_by_col = 'sales_rep_id'
            
        # created_by / updated_by
        if created_by_col:
            df['created_by'] = df[created_by_col].map(rep_to_user).fillna('USR-SYSTEM')
        else:
            df['created_by'] = 'USR-SYSTEM'
            
        df['updated_by'] = df['created_by']
        
        # updated_at
        if 'created_at' in df.columns:
            df['updated_at'] = df['created_at']
        elif 'opened_at' in df.columns:
            df['updated_at'] = df['opened_at']
        elif 'transaction_date' in df.columns:
            df['updated_at'] = df['transaction_date']
        elif 'activity_date' in df.columns:
            if 'updated_at' not in df.columns:
                df['updated_at'] = df['activity_date']
        else:
            df['updated_at'] = '2023-01-01' # Fallback
            
        if 'created_at' not in df.columns and 'opened_at' not in df.columns and 'transaction_date' not in df.columns:
             # Ensure there's at least an updated_at
             pass
             
        # deleted_at
        df['deleted_at'] = None
        
        df.to_csv(path, index=False)
        print(f"  - Added audit columns to {table}")

    print("Phase 1 enhancements completed successfully!")

if __name__ == '__main__':
    enhance_schema()
