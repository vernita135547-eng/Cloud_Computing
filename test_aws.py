import boto3


ACCESS_KEY = "YOUR_ACCESS_KEY"
SECRET_KEY = "YOUR_SECRET_KEY"

print("AWS se connect karne ki koshish kar raha hoon...")

try:
    s3_client = boto3.client(
        's3',
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY
    )
    
    
    response = s3_client.list_buckets()
    
    print("\n✅ CONNECTION SUCCESSFUL!")
    print("Aapke AWS account mein yeh buckets maujood hain:")
    print("-" * 40)
    
    for bucket in response['Buckets']:
        print(f"👉 Exact Bucket Name: '{bucket['Name']}'")
        
    print("-" * 40)
    print("Upar jo naam single quotes '' ke andar likha hai, wahi aapka REAL bucket name hai!")

except Exception as e:
    print("\n❌ CONNECTION FAILED!")
    print("Error ki details:", e)
