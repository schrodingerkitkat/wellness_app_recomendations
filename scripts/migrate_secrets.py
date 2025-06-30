#!/usr/bin/env python3
"""
Migrate hardcoded secrets to AWS Secrets Manager
Usage: python migrate_secrets.py --env production
"""
import boto3
import json
import argparse
from typing import Dict, Any

def create_secret(secrets_client: boto3.client, name: str, value: Dict[str, Any]) -> str:
    """Create or update secret in AWS Secrets Manager"""
    try:
        response = secrets_client.create_secret(
            Name=name,
            Description=f"Managed secret for {name}",
            SecretString=json.dumps(value),
            Tags=[
                {'Key': 'Environment', 'Value': args.env},
                {'Key': 'ManagedBy', 'Value': 'migration-script'},
                {'Key': 'Application', 'Value': 'wellness-app'}
            ]
        )
        return response['ARN']
    except secrets_client.exceptions.ResourceExistsException:
        # Update existing secret
        secrets_client.update_secret(
            SecretId=name,
            SecretString=json.dumps(value)
        )
        return f"arn:aws:secretsmanager:{boto3.Session().region_name}:{boto3.client('sts').get_caller_identity()['Account']}:secret:{name}"

def migrate_database_config(secrets_client: boto3.client, env: str) -> str:
    """Migrate database configuration"""
    db_config = {
        "host": f"wellness-db-{env}.cluster-xxx.us-east-1.rds.amazonaws.com",
        "port": "5432",
        "database": "wellness_app",
        "username": "app_user",
        "password": "REPLACE_WITH_ACTUAL_PASSWORD"  # Generate secure password
    }
    return create_secret(secrets_client, f"wellness-app/{env}/database", db_config)

def migrate_jwt_config(secrets_client: boto3.client, env: str) -> str:
    """Migrate JWT configuration"""
    import secrets
    jwt_config = {
        "secret_key": secrets.token_urlsafe(64),
        "algorithm": "HS256",
        "access_token_expire_minutes": 30,
        "refresh_token_expire_days": 7
    }
    return create_secret(secrets_client, f"wellness-app/{env}/jwt", jwt_config)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--env', required=True, choices=['dev', 'staging', 'production'])
    global args
    args = parser.parse_args()
    
    secrets_client = boto3.client('secretsmanager')
    
    print(f"🔐 Migrating secrets for {args.env} environment...")
    
    # Migrate database config
    db_arn = migrate_database_config(secrets_client, args.env)
    print(f"✅ Database config: {db_arn}")
    
    # Migrate JWT config
    jwt_arn = migrate_jwt_config(secrets_client, args.env)
    print(f"✅ JWT config: {jwt_arn}")
    
    print("\n📋 Update your application configuration:")
    print(f"DATABASE_SECRET_ARN={db_arn}")
    print(f"JWT_SECRET_ARN={jwt_arn}")
    
    print("\n⚠️  NEXT STEPS:")
    print("1. Update IAM role with SecretsManager:GetSecretValue permission")
    print("2. Update application code to fetch secrets from ARNs")
    print("3. Rotate database password after deployment")
    print("4. Remove hardcoded secrets from git history")

if __name__ == "__main__":
    main()