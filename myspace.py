import aws
import boto3
import botocore

""" A set of services for the use by mySpace developers """


""" get_sns_arn() returns the ARN of an SNS topic given a subname and 
function name.
paramters: function_name - a string continaing the lambda functions name
           topic - the general topic name
return: arn - string of the AWS ARN of the associated topic, None on failure
"""
def get_sns_arn(function_name, topic):
    # get list of topics
    topic_list = aws.list_sns_topics()
    if topic_list == None:
        return None

    full_topic_name = string.split(function_name, '_')[0] + '_' + topic
    if full_topic_name not in topic_list:
        return None
    return topic_list[full_topic_name]


""" raise_event() acquires the API name from the funciton_name, determines
the SNS arn from the topic and API and posts the message and subject to the 
identified topic arn.
parameters: function_name - string containing the API name
            topic - string continaing the topic name for deriving the topic arn
            message - dict containing message
            subject - string describing message
returns: True on success and False on failure
"""
def raise_event(function_name, topic, message, subject):
    # get arn
    arn = get_sns_arn(function_name, topic)
    if arn == None:
        return False

    if not aws.sns_publish(arn, message, subject):
        return False
    return True


""" get_service_state() takes a table name as a parameter and acquires the
state of the service from a dynamoDB for use by the function during its 
execution. The dictionary returned from dynamoDb looks something like this

{
"key1" : {"type1" : value1},
"key2" : {"type2" : value2}
}

The loop at the end of this method iterates over this dictionary and transforms
it to the following,

{
"key1" : value1,
"key2" : value2
}
"""
def get_service_state(table_name):
    db = boto3.client('dynamodb')
    # find the item labelled 'service_state'
    try:
        response = db.get_item(
            TableName=table_name,
            Key={
                'state' : {'S' : 'service_state'}
                }
            )
    except botocore.exceptions.ClientError as e:
        print "get_service_state(): %s" % e
        return None
    
    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        items = response['Item']
        for k, v in items.iteritems():
            items[k] = items[k][v.keys()[0]]
        return items
    else:
        return None          


""" update_service_state() takes four arguments
table_name - string
item_name - string
item_value - string
value_type - string 'S' | 'N' | 'BOOL' or other dynamoDB types

the item_name is updated to the item_value
"""
def update_service_state(table_name, item_name, item_value, value_type):
    db = boto3.client('dynamodb')
    try:
        response = db.update_item(
            TableName = table_name,
            Key = {
                'state' : {'S' : 'service_state'}
                },
            UpdateExpression = (
                'set ' + item_name + ' = :iv'
                ),
            ExpressionAttributeValues = {
                ':iv' : {value_type : item_value}
                }
            )
    except botocore.exceptions.ClientError as e:
        print "update_service_state(): %s" % e
        return False

    # test for failure
    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        return True
    else:
        return False


""" delete_lambda() removes the lambda function associated with the service
parameters: service_name
returns: True on success and False on failure
"""
def delete_lambda(service_name):
    # delete assocaited lambda function
    function_list = aws.list_functions()
    if service_name in function_list:
        if not aws.delete_function(function_list[service_name]):
            return False
    return True


""" delete_sns() deletes sns topics and subscriptions associated with service
paramters: service_name
returns: True on success and False on failure
"""
def delete_sns(service_name):
    # delete SNS services
    topic_list = aws.list_sns_topics()
    if service_name in topic_list:
        if not aws.delete_sns_topic(topic_list[service_name]):
            return False
    return True


""" delete_dynamodb() removes the database tables associated with service
paramters: service_name
returns: True on success and False on failure
"""
def delete_dynamodb(service_name):
    db_list = aws.list_dynamodb_tables()
    if service_name in db_list:
        if not aws.delete_dynamodb_table(service_name):
            return False
    return True


""" delete_resource() deletes a resource from the identified API
parameters: api_name
            resource_path
returns: True on success and False on failure
"""
def delete_resource(api_name, resource_path):
    if not aws.delete_api_resource(api_name, resource_path):
        return False
    return True
