# ATProto (Account Portability Protocol)

## What is AT Protocol?

AT Protocol (Authenticated Transfer Protocol) is an open social networking protocol developed by Bluesky. It's designed to create a decentralized social web where users have control over their data and can move between different services while maintaining their social connections.

## Key Features

### 1. Account Portability

- Users can move their accounts between different services
- Maintain your identity and social graph across platforms
- No vendor lock-in

### 2. Algorithmic Choice

- Users can choose their own algorithms for content discovery
- Different services can implement different recommendation systems
- Freedom to switch between different algorithms

### 3. Interoperable Data

- Standardized data formats for social content
- Easy sharing and interaction between different services
- Common protocol for social features

## Core Components

### 1. Personal Data Servers (PDS)

- Store user data and content
- Handle user authentication
- Manage user preferences and settings

### 2. Big Graph Service (BGS)

- Indexes and aggregates data across the network
- Enables content discovery
- Manages social graph data

### 3. App Views

- User interfaces for interacting with the protocol
- Can be customized by different services
- Provide different features and experiences

## Technical Architecture

### 1. Data Structure

- Uses IPLD (InterPlanetary Linked Data) for content addressing
- Implements CRDTs (Conflict-free Replicated Data Types) for synchronization
- Uses DIDs (Decentralized Identifiers) for identity

### 2. Authentication

- Uses UCAN (User Controlled Authorization Networks)
- Secure and flexible permission system
- Supports delegation and revocation

### 3. Content Types

- Standardized formats for posts, likes, reposts
- Extensible for new content types
- Supports rich media and links

## Getting Started

### Basic Concepts

1. **DID**: Your unique identifier in the network
2. **Handle**: Your human-readable username
3. **Repository**: Your personal data store
4. **Records**: Individual pieces of content

### Common Operations

- Creating and managing posts
- Following other users
- Interacting with content
- Managing your data

## Development

### SDKs and Tools

- Official atproto SDKs for various languages
- Development tools and documentation
- Testing environments

### Building on AT Protocol

- Creating custom apps
- Implementing new features
- Contributing to the protocol

## Resources

- [AT Protocol Documentation](https://atproto.com/docs)
- [Bluesky GitHub](https://github.com/bluesky-social)
- [Protocol Specification](https://atproto.com/specs)
