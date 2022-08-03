# Author: Noor Ul Ain Butt
# --------------------------

from datetime import datetime
from pprint import pprint
from time import sleep
from unicodedata import name
from unittest import result
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from sqlalchemy import false, true
import array as arr
import numpy as np

def prompt():

    print("Welcome to Kubernetes Script.\n\n")
    environmentName = input("Kindly enter the environment name you want to access.\n")
    if ( environmentName == "exit" ):
        exit(0)

    return environmentName

   

def checkEnvironmentAvailability( instance, environmentName ):

    environmentList = []

    try:
        environmentObjects = instance.list_namespace()
    except ApiException as exp:
        print("Exception when calling BatchV1Api -> list_namespace: %s \n" % exp)


    for object in environmentObjects.items:
        environmentList.append(object.metadata.name)


    environmentArray = np.array(environmentList)
    
    nameExists = environmentName in environmentArray

    if (nameExists):
        return True, environmentName
    else:
        return False, environmentName


def listJobs(apiInstance, environmentName ):
      
        jobNamesList = []  

        try:
            apiInstanceResponse = apiInstance.list_namespaced_job( namespace = environmentName, pretty = "true" )

            for object in apiInstanceResponse.items:
                jobNamesList.append(object.spec.template.metadata.name)
            
            jobNamesArray = np.array(jobNamesList)

            return jobNamesArray

        except ApiException as exp:
            print("Exception when calling BatchV1Api -> list_namespaced_job: %s \n" % exp)



def selectJob( apiInstance, jobName, envName ):

    # print("Inside selectjob method")
    if ( jobName == "exit"):
        exit(0)

    try:
        apiInstanceResponse = apiInstance.read_namespaced_job(
        name = jobName,
        namespace = envName,
        pretty = "true"
        )
        return apiInstanceResponse
    except ApiException as exp:
        print("Exception when calling BatchV1Api -> read_namespaced_job: %s \n" % exp)


    
def createJobObject(selectedJobObject):

    # variable extraction
    containerNameFetched = selectedJobObject.spec.template.spec.containers[0].name
    containerName = containerNameFetched + "-manual"
    imageName = selectedJobObject.spec.template.spec.containers[0].image
    imagePullPolicy = selectedJobObject.spec.template.spec.containers[0].image_pull_policy
    envObject = selectedJobObject.spec.template.spec.containers[0].env
    shellCommand = ['sh', '-c', 'yarn migrate']
    # selectedJobObject.spec.template.spec.containers[0].command
    
    container = client.V1Container(
        name = containerName,
        image = imageName,
        image_pull_policy = imagePullPolicy,
        env = envObject,
        command = shellCommand
    )

    podSpec = client.V1PodSpec(
        restart_policy = "OnFailure",
        containers =  [container] 
    )

    podTemplateSpec = client.V1PodTemplateSpec(
        spec = podSpec,
    )

    jobSpec = client.V1JobSpec(
        template = podTemplateSpec,
        backoff_limit = 5 
    )

    metadataName = client.V1ObjectMeta( name = containerName)

    job = client.V1Job(
        api_version = "batch/v1",
        kind = "Job",
        metadata = metadataName,
        spec = jobSpec
    )

    # jobTemplateSpec = client.V1JobTemplateSpec( spec = jobSpec )

    # cronJobSpec = client.V1CronJobSpec( 
    # schedule = "* * * * *", 
    # concurrency_policy = "Forbid", 
    # starting_deadline_seconds = 120, 
    # successful_jobs_history_limit = 1, 
    # job_template = jobTemplateSpec
    # )


    # cronJob = client.V1CronJob(
    #     api_version = "batch/v1",
    #     kind = "CronJob",
    #     metadata = metadata,
    #     spec = cronJobSpec
    # )

    # if (cronJob):
    #     print("CronJob Object creation successful:")
    #     pprint(cronJob)
    # else:
    #     print("Could not create cron job object")

    return job


def createJob(apiInstance, jobObject, enviornmentName):
    
    try:
        apiInstanceResponse = apiInstance.create_namespaced_job(
            body = jobObject,
            namespace = enviornmentName,
            pretty = "true"
        )
        print("Job created. status='%s'" % str(apiInstanceResponse.status))
        returnJobName = jobObject.spec.template.spec.containers[0].name

        return true, returnJobName

    except ApiException as exp:
        print("Exception when calling BatchV1Api->create_namespaced_job: %s\n" % exp)


def deleteJob(apiInstance, jobName, enviornmentName):

    try:
        apiInstanceResponse = apiInstance.delete_namespaced_job(
            name = jobName,
            namespace = enviornmentName,
            body = client.V1DeleteOptions(
                propagation_policy='Foreground',
                grace_period_seconds=0),
            pretty = "true"
            )

        print("Job deleted. status='%s'" % str(apiInstanceResponse.status))
        return true

    except ApiException as exp:
        print("Exception when calling BatchV1Api -> delete_namespaced_job: %s\n" % exp)


def main():
    
    # loading kubeconfig
    config.load_kube_config()

    # loading kubernetes Batch API model
    instance = client.BatchV1Api()

    # loading kubernetes Batch API model
    instanceCoreV1Api = client.CoreV1Api()

    # calling prompt function for opeing message
    envNameOnPrompt = prompt()

    # checking enviornment availability on cluster
    status, envName = checkEnvironmentAvailability( instanceCoreV1Api , envNameOnPrompt)

    # iteration untill correct environment is selected
    while ( status != True ):
        envNameOnPromp = prompt()
        newStatus, envName = checkEnvironmentAvailability( instanceCoreV1Api, envNameOnPromp )
        status = newStatus
    
    print("\n")

    # listing all the jobs in an environment
    jobs = listJobs( instance, environmentName = envName )
    print("Following are the jobs in %s environment:\n" % envName)

    
    # pringing available jobs
    for jobNames in jobs:
        print(jobNames)

    
    # user input for job to be created
    selectedJobName = input("\nKindly select a job to create from above list.\n")

    
    # selecting and retreiving the job to be created
    selectedJob = selectJob( instance,envName = envName, jobName = selectedJobName )

    
    # creating a new job object for the selected job
    jobObject = createJobObject( selectedJob )
    

    # creating the new job
    jobCreated = createJob( instance, jobObject = jobObject, enviornmentName = envName )

    # extracting job name and its status of creation
    boolean , jobName = jobCreated 


    if boolean:
        print( "Success\n" )
        print("Your job will be deleted in 60 seconds after its execution.\n")

        # a delay for deleting the job after its execution
        sleep(60)

        # deleting the job
        result = deleteJob( apiInstance = instance, enviornmentName = envName, jobName = jobName )
        if result:
            exit(0)
    else:
        print( "Failure" )
        exit(1)


if __name__ == '__main__':
    main()