import boto3
import paramiko
import json
import time

def lambda_handler(event, context):
    cluster_list = []
    private_ip = []
    instance_id=[]
    terminate_ins=[]
    ecs_client = boto3.client('ecs')
    ec2_client = boto3.client('ec2')
    SES = boto3.client('ses')
    
    SENDER_EMAIL = "sender@gmail.com"
    DEVOPS_EMAIL_DL = ["receiver@gmail.com"]
    
    #-------------------- MAIL Fucntion--------------------------#
    
    def send_email(email_to,sub,body):
        response = SES.send_email(
            Source=SENDER_EMAIL,
            Destination={
                'ToAddresses': email_to
            },
            Message={
                'Subject': {
                    'Data': sub
                },
                'Body': {
                    'Text': {
                        'Data': body
                    }
                }
            },
            ReturnPath='sender@gmail.com'
        )
        
    #--------------------Fucntion END----------------------------#
    
    #--------------------Instance Terminate Fucntion -------------#
    
    def terminate_instance(del_instance):
        terminate_ins.append(del_instance)
        print(ec2_client.terminate_instances(InstanceIds=del_instance))
    
    #--------------------Fucntion END-----------------------------#
    
    cluster_response = ecs_client.list_clusters()
    cluster_list=cluster_response['clusterArns']
    for i in range(len(cluster_list)):
        if "cluster-name" in cluster_list[i]: # If you want to skip any cluster you can mention name of cluster in "cluster-name"
            pass
        else:
            container_response = ecs_client.list_container_instances(  # From here we get all cluster container instances whose agent connected is false
            cluster= cluster_list[i],
            filter= 'agentConnected == true',
            maxResults=50,
            status='ACTIVE'
            )
            for j in range(len(container_response['containerInstanceArns'])): # From here we get list of containers whose agent connected if false
                container_arn = container_response['containerInstanceArns'][j][-32:]
                
                cont_instances = ecs_client.describe_container_instances( # From here we are fetching container details
                    cluster=cluster_list[i],
                    containerInstances=[
                    container_arn
                    ],
                )
                instance_Id = cont_instances['containerInstances'][0]['ec2InstanceId'] # From here we fetching instance id from container details
                
                desc_instances = ec2_client.describe_instances( # From here we fetching instance details with the help of instance id
                    InstanceIds=[
                    instance_Id 
                    ]
                )
                private_ip.append(desc_instances['Reservations'][0]['Instances'][0]['PrivateIpAddress']) # Here we are storing all private ip into list for ssh
                instance_id.append(instance_Id) # Here we are storing instance id
    print(private_ip)
    sub_data = 'WARNING :- LIST OF INSTANCE WHOSE AGENT IS "FALSE" '
    sub_msg = "IP ADDRESS of ECS Instances :- "
    str1 = "\n" 
    body_data=str1.join(private_ip)
    body_data=sub_msg+"\n"+body_data
    email_to = DEVOPS_EMAIL_DL
    send_email(email_to,sub_data,body_data)
    print(instance_id)


#--------------------Here we will do ssh on every instance that is present in private_ip list-------------------------------------#


    s3_client = boto3.client('s3')
    s3_client.download_file('python1-lib', 'dev.pem','/tmp/dev.pem') # Download key from s3 bucket and stored in /tmp
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    key = paramiko.RSAKey.from_private_key_file("/tmp/dev.pem") 
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

#----------------------------------Function START------------------------------------------------------------#

    def agentstart(host): # Function for ssh into private_ip 
        try:
            print("Connecting to : " + host)
            ssh_client.connect(hostname=host, username="ec2-user", pkey=key)
            print("Connected to :" + host)
            commands = ["touch /tmp/pawan.txt","sudo systemctl status ecs"]
            for command in commands:
                if command == "touch /tmp/pawan.txt": # Start ECS agent
                    print(command)
                    stdin, stdout, stderr = ssh_client.exec_command(command)
                    #time.sleep(30)
                if command == "sudo systemctl status ecs": # Check agent is started or not
                    print(command)
                    count = 0
                    while count < 5:
                        stdin, stdout, stderr = ssh_client.exec_command(command)
                        c=stdout.readlines()
                        print(c[2])
                        if "active" in c[2]:
                            print("agent started")
                            break
                        else:
                            stdin, stdout, stderr = ssh_client.exec_command("sudo systemctl start ecs")
                            count = count+1
                            
                    if count>3:
                        terminate_instance(instance_id(public_ip.index(host))) # terminating instance 
        except:
            print("----ERROR-----")
            pass
#------------------------------------------------Function END ------------------------------------------------------#
            
    if len(terminate_ins) > 0:
        sub_dataa = 'WARNING :- LIST OF TERMINATED INSTANCE '
        sub_msg2 = "Terminated ECS Instance IP ADDRESS :- "
        str2 = "\n" 
        body_dataa=str2.join(terminate_ins)
        body_dataa=sub_msg2+"\n"+body_dataa
        email_to = DEVOPS_EMAIL_DL
        send_email(email_to,sub_dataa,body_dataa)
