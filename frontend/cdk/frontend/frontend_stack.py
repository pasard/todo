from aws_cdk import (
    CfnOutput,
    Duration,
    Stack,
    aws_s3 as s3,
    aws_s3_deployment as s3_deployment,
    aws_cloudfront as cloudfront
)
from constructs import Construct

class FrontendStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.frontend_source_bucket = s3.Bucket(self, "FrontendAppBucket",
          website_index_document="index.html",
        )

        self.frontend_orgin_access_identity = cloudfront.OriginAccessIdentity(self, "FrontendAppOIA", 
          comment="Access from CloudFront to the bucket."
        )

        self.frontend_source_bucket.grant_read(self.frontend_orgin_access_identity)

        self.frontend_cloudfront = cloudfront.CloudFrontWebDistribution(self, "FrontendAppCloudFront",
          origin_configs=[cloudfront.SourceConfiguration(
            s3_origin_source=cloudfront.S3OriginConfig(
              s3_bucket_source=self.frontend_source_bucket,
              origin_access_identity=self.frontend_orgin_access_identity
            ),
            behaviors=[cloudfront.Behavior(is_default_behavior=True)]
          ), cloudfront.SourceConfiguration(
            custom_origin_source=cloudfront.CustomOriginConfig(
              domain_name=f"{self.node.try_get_context('api_domain')}",
              origin_path=f"/{self.node.try_get_context('api_stage')}",
              http_port=80,
              https_port=443,
              origin_protocol_policy=cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
              allowed_origin_ssl_versions=[cloudfront.OriginSslPolicy.TLS_V1_2]
            ),
            behaviors=[
              cloudfront.Behavior(
                path_pattern="/api/*",
                allowed_methods=cloudfront.CloudFrontAllowedMethods.ALL,
                cached_methods=cloudfront.CloudFrontAllowedCachedMethods.GET_HEAD_OPTIONS,
                default_ttl=Duration.seconds(0),
                min_ttl=Duration.seconds(0),
                max_ttl=Duration.seconds(0),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                forwarded_values=cloudfront.CfnDistribution.ForwardedValuesProperty(
                  query_string=True,
                  cookies=cloudfront.CfnDistribution.CookiesProperty(
                      forward="all"
                  ),
                  headers=["Authorization"]
                )
              )
            ]
          )],
          error_configurations=[cloudfront.CfnDistribution.CustomErrorResponseProperty(
            error_code=404,
            error_caching_min_ttl=0,
            response_code=200,
            response_page_path="/index.html"
          )]
        )

        s3_deployment.BucketDeployment(self, "FrontendAppDeploy",
          sources=[s3_deployment.Source.asset(
            path="frontend/build"
          )],
          destination_bucket=self.frontend_source_bucket,
          distribution=self.frontend_cloudfront,
          distribution_paths=["/*"]
        )

        CfnOutput(self, "AppURL", value=f"https://{self.frontend_cloudfront.distribution_domain_name}/")

