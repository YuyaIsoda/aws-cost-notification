#!/usr/bin/env python
# encoding: utf-8

import json
import datetime
import boto3
import os
import logging

# Additional
# https://github.com/UnitedIncome/serverless-python-requirements
try:
    import unzip_requirements
except ImportError:
    pass

import requests

# Log setting
logging.basicConfig(level=logging.INFO)

# Budget Setting
bgt = boto3.client('budgets')
AccountId   = os.getenv('AccountId', '123456789')
BudgetName  = os.getenv('BudgetName', 'aws_cost_notification')
LimitUSD    = os.getenv('LimitUSD', 1000)
NtThreshold = os.getenv('NtThreshold', 80)
NtEmail     = os.getenv('NtEmail', None)
MSTeamsUrl  = os.getenv('MSTeamsUrl', None)

# Get Budgets
def get_budgets():
    try:
        res = bgt.describe_budgets(AccountId=AccountId)
    except Exception as e:
        logging.error("Request failed: %s", e)
        raise e
    return res

def get_budget():
    try:
        res = bgt.describe_budget(AccountId=AccountId, BudgetName=BudgetName)
    except Exception as e:
        logging.error("Request failed: %s", e)
        raise e

    budget  = res['Budget']['BudgetLimit']['Amount']
    actual  = res['Budget']['CalculatedSpend']['ActualSpend']['Amount']
    forecast= res['Budget']['CalculatedSpend']['ForecastedSpend']['Amount']
    dtime   = datetime.datetime.now()

    body    = {
        'color': '#008000', # green
        'text': {
            'date': dtime.strftime('%Y/%m/%d'),
            'message': 'Within budget',
            'cost': {
                'budget': budget,
                'actual': actual,
                'forecast': forecast
            }
        }
    }

    if float(budget) <= float(forecast):
        body['color'] = '#FFFF00' # yellow
        body['text']['message'] = 'Cost will be over budget!'
    elif float(budget) <= float(actual):
        body['color'] = '#FF0000' # red
        body['text']['message'] = 'Cost was already over budget!!'
    logging.info(body)
    return body

def create_budget():
    Budget = {
        'BudgetName': BudgetName,
        'BudgetType': 'COST',
        'BudgetLimit': {
            'Amount': str(LimitUSD),
            'Unit': 'USD'
        },
        'TimeUnit': 'MONTHLY'
    }

    Subscribers = [
        {
            'Notification': {
                'NotificationType': 'FORECASTED',
                'ComparisonOperator': 'GREATER_THAN',
                'Threshold': int(NtThreshold),
                'ThresholdType': 'PERCENTAGE',
                'NotificationState': 'ALARM'
            },
            'Subscribers': [
                {
                    'SubscriptionType': 'EMAIL',
                    'Address': str(NtEmail)
                }
            ]
        }
    ]

    if NtEmail == None:
        Subscribers = []

    try:
        res = bgt.create_budget(AccountId = AccountId, Budget = Budget,
                NotificationsWithSubscribers = Subscribers
            )
        logging.debug(res)
    except Exception as e:
        logging.error("Request failed: %s", e)
        raise e
    return res

def delete_budget():
    try:
        res = bgt.delete_budget(AccountId=AccountId, BudgetName=BudgetName)
        logging.debug(res)
    except Exception as e:
        logging.error("Request failed: %s", e)
        raise e
    return res

# Notifications
def nt_msteams(body):
    if MSTeamsUrl == None:
        return None

    message = {
        '@type': "MessageCard",
        '@context': "http://schema.org/extensions",
        'themeColor': body['color'],
        'summary': "budget",
        'text': json.dumps(body['text'])
    }

    try:
        req = requests.post(MSTeamsUrl, data=json.dumps(message))
        logging.info("Message posted to %s", "teams")
    except requests.exceptions.RequestException as e:
        logging.error("Request failed: %s", e)
    return None

# Main
def m_notification(event, context):
    body = get_budget()
    nt_msteams(body=body)
    return None

def m_create(event, context):
    create_budget()
    return None

def m_delete(event, context):
    delete_budget()
    return None

if __name__ == "__main__":
    get_budgets()
    #m_create('', '')
    #m_delete('', '')

