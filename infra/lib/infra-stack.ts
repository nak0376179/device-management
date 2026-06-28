import * as cdk from 'aws-cdk-lib/core';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import { Construct } from 'constructs';

export class InfraStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Groups table: PK=group_id
    new dynamodb.Table(this, 'GroupsTable', {
      tableName: 'Groups',
      partitionKey: { name: 'group_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // Devices table: PK=group_id, SK=dev_id + GSI(api_key-index)
    const devicesTable = new dynamodb.Table(this, 'DevicesTable', {
      tableName: 'Devices',
      partitionKey: { name: 'group_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'dev_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    devicesTable.addGlobalSecondaryIndex({
      indexName: 'api_key-index',
      partitionKey: { name: 'api_key', type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // Tasks table: PK=device_pk, SK=task_id
    new dynamodb.Table(this, 'TasksTable', {
      tableName: 'Tasks',
      partitionKey: { name: 'device_pk', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'task_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });
  }
}
