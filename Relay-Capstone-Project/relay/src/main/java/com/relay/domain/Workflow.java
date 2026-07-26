package com.relay.domain;

import jakarta.persistence.*;
import java.time.OffsetDateTime;
import java.util.UUID;

@Entity
@Table(name = "workflows")
public class Workflow {

    @Id
    @GeneratedValue
    private UUID id;

    @Column(nullable = false)
    private String name;

    /** HMAC secret used to verify webhook triggers. */
    @Column(nullable = false)
    private String secret;

    @Column(name = "published_version_id")
    private UUID publishedVersionId;

    @Column(name = "created_at", nullable = false)
    private OffsetDateTime createdAt = OffsetDateTime.now();

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public String getSecret() { return secret; }
    public void setSecret(String secret) { this.secret = secret; }

    public UUID getPublishedVersionId() { return publishedVersionId; }
    public void setPublishedVersionId(UUID publishedVersionId) { this.publishedVersionId = publishedVersionId; }

    public OffsetDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(OffsetDateTime createdAt) { this.createdAt = createdAt; }
}
