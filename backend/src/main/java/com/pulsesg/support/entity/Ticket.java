package com.pulsesg.support.entity;

import jakarta.persistence.*;
import java.time.Instant;

@Entity @Table(name="tickets")
public class Ticket {
 @Id @GeneratedValue(strategy=GenerationType.IDENTITY) private Long id;
 @ManyToOne(fetch=FetchType.LAZY,optional=false) @JoinColumn(name="user_id") private User user;
 @Column(nullable=false) private String title; @Column(nullable=false,columnDefinition="TEXT") private String description;
 @Enumerated(EnumType.STRING) private Category category; @Enumerated(EnumType.STRING) private Priority priority; @Enumerated(EnumType.STRING) private Status status;
 private Instant createdAt; private Instant updatedAt;
 @PrePersist void created(){createdAt=updatedAt=Instant.now(); if(status==null)status=Status.OPEN;} @PreUpdate void updated(){updatedAt=Instant.now();}
 public enum Category{ACCOUNT,BILLING,TECHNICAL,GENERAL,OTHER} public enum Priority{LOW,MEDIUM,HIGH,CRITICAL} public enum Status{OPEN,IN_PROGRESS,RESOLVED,CLOSED}
 public Long getId(){return id;} public User getUser(){return user;} public void setUser(User v){user=v;} public String getTitle(){return title;} public void setTitle(String v){title=v;} public String getDescription(){return description;} public void setDescription(String v){description=v;} public Category getCategory(){return category;} public void setCategory(Category v){category=v;} public Priority getPriority(){return priority;} public void setPriority(Priority v){priority=v;} public Status getStatus(){return status;} public void setStatus(Status v){status=v;} public Instant getCreatedAt(){return createdAt;} public Instant getUpdatedAt(){return updatedAt;}
}
