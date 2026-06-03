package com.insuramind.document;

import com.insuramind.common.ApiException;
import io.minio.BucketExistsArgs;
import io.minio.GetPresignedObjectUrlArgs;
import io.minio.MakeBucketArgs;
import io.minio.MinioClient;
import io.minio.PutObjectArgs;
import io.minio.http.Method;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.InputStream;
import java.util.concurrent.TimeUnit;

@Service
public class MinioStorageService {
    private final MinioClient minioClient;
    private final String bucket;
    private final String endpoint;
    private final String publicEndpoint;

    public MinioStorageService(
            MinioClient minioClient,
            @Value("${app.minio.bucket}") String bucket,
            @Value("${app.minio.endpoint}") String endpoint,
            @Value("${app.minio.public-endpoint}") String publicEndpoint
    ) {
        this.minioClient = minioClient;
        this.bucket = bucket;
        this.endpoint = endpoint;
        this.publicEndpoint = publicEndpoint;
    }

    public void upload(String objectKey, MultipartFile file) {
        try {
            ensureBucket();
            try (InputStream stream = file.getInputStream()) {
                minioClient.putObject(PutObjectArgs.builder()
                        .bucket(bucket)
                        .object(objectKey)
                        .stream(stream, file.getSize(), -1)
                        .contentType(file.getContentType())
                        .build());
            }
        } catch (Exception ex) {
            throw new ApiException(HttpStatus.BAD_GATEWAY, "Could not store file: " + ex.getMessage());
        }
    }

    public String signedUrl(String objectKey, int seconds) {
        try {
            ensureBucket();
            String url = minioClient.getPresignedObjectUrl(GetPresignedObjectUrlArgs.builder()
                    .method(Method.GET)
                    .bucket(bucket)
                    .object(objectKey)
                    .expiry(seconds, TimeUnit.SECONDS)
                    .build());
            return url.replace(endpoint, publicEndpoint);
        } catch (Exception ex) {
            throw new ApiException(HttpStatus.BAD_GATEWAY, "Could not create file URL: " + ex.getMessage());
        }
    }

    private void ensureBucket() throws Exception {
        boolean exists = minioClient.bucketExists(BucketExistsArgs.builder().bucket(bucket).build());
        if (!exists) {
            minioClient.makeBucket(MakeBucketArgs.builder().bucket(bucket).build());
        }
    }
}
