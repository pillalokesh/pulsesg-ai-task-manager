package com.pulsesg.support.entity;

import jakarta.persistence.*;
import java.time.Instant;

@Entity @Table(name="users")
public class User {
 @Id @GeneratedValue(strategy=GenerationType.IDENTITY) private Long id;
 @Column(nullable=false) private String fullName;
 @Column(nullable=false,unique=true) private String email;
 @Column(nullable=false) private String passwordHash;
 private Instant createdAt; private Instant updatedAt;
 @PrePersist void created(){createdAt=updatedAt=Instant.now();} @PreUpdate void updated(){updatedAt=Instant.now();}
 public Long getId(){return id;} public String getFullName(){return fullName;} public void setFullName(String v){fullName=v;} public String getEmail(){return email;} public void setEmail(String v){email=v;} public String getPasswordHash(){return passwordHash;} public void setPasswordHash(String v){passwordHash=v;} public Instant getCreatedAt(){return createdAt;} public Instant getUpdatedAt(){return updatedAt;}
}
