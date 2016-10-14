from __future__ import print_function

import aws
import boto3
import json
import myspace
import string

""" The myspace module imported above simplifies mySpace development. It 
contains functions to simplify function state manipulation and deleting AWS
resources when the service is deleted.
"""
    
""" send_SMS takes as parameters phone_number, body and subject. The body and
subject are sent to the owner via SMS to the provided phone number. This feature
is not yet complete.
"""
def send_SMS(phone_number, body, subject):
    # create sns client    
    sns = boto3.client('sns')
    # send SMS
    response = sns.publish(
        PhoneNumber = phone_number,
        Message = body,
        Subject = subject
        )
    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        return True
    else:
        return False
    return True       


""" send_email takes as parameters from_addr, to_addr, body, and subject
and sends the body and subject to the owner from the from_addr via aws ses.
"""
def send_email(from_addr, to_addr, body, subject):
    # create email client    
    ses = boto3.client('ses')
    # send email
    response = ses.send_email(
        Source=from_addr,
        Destination={'ToAddresses': [to_addr]},
        Message={
            'Subject': {
                'Data': subject,
                'Charset': 'utf-8'
                },
            'Body': {
                'Text': {
                    'Data': body,
                    'Charset': 'utf-8'
                    }
                }
            }
        )
    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        return True
    else:
        return False


""" send_notification sends the body and subject to the recipient identified
in the services state via email and sms as indicated in the service state. SMS 
is not yet implemented.
"""
def send_notification(table_name, from_addr, body, subject):
    # get state from dynamoDB
    state = myspace.get_service_state(table_name)
    if state == None:
        return False

    # make notifications
    if state['email_notify'] is True:
        # send email to owner
        response = send_email(from_addr, state['email_address'], body, subject)
        if response is not True:
            return False
        
    if state['sms_notify'] is True:
        # send SMS to owner
        response = send_SMS(state['sms_number'], body, subject)
        if response is not True:
            return False
    
    return True


""" delete_resources() deletes all of the aws resources associated with this
service.
parameters: resource_path
            function_name (includes namespaced prefix added at install)
returns: True on success and False on failure
"""
def delete_resources(resource_path, service_name):
    # delete assocaited lambda function
    if not myspace.delete_lambda(service_name):
        print('failed to delete lambda function {}'.format(service_name))
            
    # delete SNS services
    sns_name = service_name + '_' + 'request'
    if not myspace.delete_sns(sns_name):
        print('failed to delete SNS topic {}'.format(sns_name))

    # delete dynamoDB services
    if not myspace.delete_dynamodb(service_name):
        print('failed to delete dynamoDB table {}'.format(service_name))

    # delete API resource
    api_name = string.split(service_name, '_')[0]
    if not myspace.delete_resource(api_name, resource_path):
        print('failed to delete API resource {}'.format(resource_path))
        
    return True


def owner_notification(event, context):
    # determine how we were invoked
    # test to see if called via API
    if 'resource_path' in event:
        # called by owner_notification API, react to HTTP methods
        if event['http_method'] == 'GET':
            # get state from dynamoDB and return
            state = myspace.get_service_state(context.function_name)
            if state != None:
                del state['state']
                return state
            else:
                raise Exception('Server Error')
        
        elif event['http_method'] == 'PUT':
            valid_string_list = [
                'email_address',
                'sms_number'
                ]
            valid_boolean_list = [
                'email_notify',
                'sms_notify'
                ]

            for item in valid_string_list:
                if item not in event:
                    raise Exception('Server Error')
                else:
                    # verify new email address
                    if item == 'email_address':
                        if not aws.verify_email_address(event[item]):
                            raise Exception('Server Error')
                    if not myspace.update_service_state(context.function_name, item, event[item], 'S'):
                        raise Exception('Server Error')

            for item in valid_boolean_list:
                if item not in event:
                    raise Exception('Server Error')
                else:
                    if not myspace.update_service_state(context.function_name, item, event[item], 'BOOL'):
                        raise Exception('Server Error')

            return

        elif event['http_method'] == 'POST':
            valid_string_list = [
                'from_address',
                'body',
                'subject'
                ]
            for item in valid_string_list:
                if item not in event:
                    raise Exception('Server Error')

            success = send_notification(
                context.function_name,
                event['from_address'],
                event['body'],
                event['subject']
                )
            if success:
                return
            else:
                raise Exception('Server Error')
        
        elif event['http_method'] == 'DELETE':
            success = delete_resources(
                event['resource_path'],
                context.function_name
                )
            if success:
                return
            else:
                raise Exception('Server Error')

        else:
            raise Exception('MethodNotAllowed')
            
    else:
        # invoked by an SNS event
        sns = event['Records'][0]['Sns']
        if sns['Subject'] != 'OwnerNotificationRequest':
            return
        event_message = json.loads(sns['Message'])

        # notify owner
        success = send_notification(
            context.function_name,
            event_message['from_address'],
            event_message['body'],
            event_message['subject']
            )
        if success:
            return
        else:
            raise Exception('Server Error')
