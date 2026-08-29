Temple Charity Website — Sri Balaganapathi Seva Mandali

A secure full-stack temple donation management system built for Sri Balaganapathi Seva Mandali, allowing devotees to register, authenticate, and make online donations while providing administrators with secure management capabilities.

Features
🔐 JWT Authentication — Secure user registration and login with role-based access.
👤 User & Donor Management — Manage donor profiles and enforce donor ownership.
💰 Donation Management — Authenticated users can create donations securely.
💳 Razorpay Integration — Payment order creation, signature verification, and webhook support.
🛕 Temple Information — Public access to events, seva offerings, and gallery.
👨‍💼 Admin Dashboard — Protected administrative APIs for managing donors, donations, and temple data.
🗄️ PostgreSQL Database — Reliable relational data storage with JPA/Hibernate.
🔄 Flyway Migrations — Version-controlled and consistent database schema management.
🌐 Responsive React Frontend — Modern interface connected to the Spring Boot REST APIs.
🛡️ Centralized Error Handling — Proper handling of validation, authentication, authorization, and database errors.
Tech Stack
Frontend
React
TypeScript
Vite
HTML5
CSS3
Backend
Java
Spring Boot 3
Spring Security
JWT
Spring Data JPA
Hibernate
Maven
Database & Infrastructure
PostgreSQL 16
Flyway
Docker
Payments
Razorpay
Architecture
┌──────────────────────┐
│      React/Vite      │
│      Frontend        │
└──────────┬───────────┘
           │ REST API
           │ /api/*
           ▼
┌──────────────────────┐
│    Spring Boot       │
│      Backend         │
├──────────────────────┤
│ Spring Security      │
│ JWT Authentication   │
│ REST Controllers     │
│ Services             │
│ JPA / Hibernate      │
└───────┬───────┬──────┘
        │       │
        ▼       ▼
┌────────────┐ ┌────────────┐
│ PostgreSQL │ │  Razorpay  │
│  Database  │ │  Payments  │
└────────────┘ └────────────┘
Authentication & Authorization

The application uses JWT-based authentication with two primary roles:

Role	Access
ROLE_USER	Login, profile/donor-owned donation operations
ROLE_ADMIN	Donor management, donation management, administrative operations

Public endpoints such as temple events, seva offerings, gallery, and health status do not require authentication.

Administrative endpoints are protected using Spring Security and method-level authorization.

API Overview
Public APIs
GET  /api/health
GET  /api/events
GET  /api/seva-offerings
GET  /api/gallery
Authentication
POST /api/auth/register
POST /api/auth/login
Donors
GET    /api/donors
POST   /api/donors
PUT    /api/donors/{id}
DELETE /api/donors/{id}
Donations
POST   /api/donations
GET    /api/donations
GET    /api/donations/{id}
PUT    /api/donations/{id}
DELETE /api/donations/{id}
Payments
POST /api/payments/orders
POST /api/payments/verify
POST /api/payments/webhook
Admin
GET /api/admin/dashboard
Database

PostgreSQL runs through Docker.

Default development configuration:

Host: localhost
Port: 5433
Database: sribalaganapathi_v2

Flyway manages database migrations and keeps the application schema synchronized.

Environment Variables

Create a .env file based on .env.example.

Example:

DB_HOST=localhost
DB_PORT=5433
DB_NAME=sribalaganapathi_v2
DB_USER=temple_app
DB_PASSWORD=your_database_password

JWT_SECRET=your_strong_jwt_secret
JWT_EXPIRATION=3600000

ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=your_admin_password

RAZORPAY_KEY_ID=your_test_key_id
RAZORPAY_KEY_SECRET=your_test_key_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret

Never commit .env or real credentials to GitHub.

Running the Project
1. Start PostgreSQL

From the project root:

docker compose up -d

Verify the database container:

docker ps
2. Start Backend
cd backend
mvn spring-boot:run

Backend runs on:

http://localhost:8080
3. Start Frontend

Open another terminal:

cd frontend
npm install
npm run dev

Frontend normally runs on:

http://localhost:5173
Verification

The backend has been verified for:

Health endpoint — 200 OK
Public events API — 200 OK
Public seva API — 200 OK
Public gallery API — 200 OK
User registration — 201 Created
Duplicate registration — 409 Conflict
Valid user login — 200 OK
Invalid credentials — 401 Unauthorized
Unauthorized admin access — 403 Forbidden
Admin authentication and protected access
PostgreSQL connectivity
Flyway migration validation
Spring Boot startup
JWT role handling
Project Structure
SriBalaganapathiV2/
│
├── backend/
│   ├── src/
│   │   └── main/
│   │       ├── java/
│   │       └── resources/
│   │           └── db/
│   │               └── migration/
│   ├── pom.xml
│   └── README.md
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
│
├── docker-compose.yml
├── .env.example
└── .gitignore
Security

The project follows several security practices:

Passwords are stored as secure hashes rather than plaintext.
JWT authentication protects secured APIs.
Role-based authorization separates users and administrators.
Donor ownership is validated before donation creation.
Razorpay signatures are verified server-side.
Webhook requests require signature validation.
Database schema changes are managed through Flyway.
Sensitive environment variables are excluded from version control.
Future Improvements
Production Razorpay configuration
Production deployment
Automated unit and integration test coverage
Enhanced admin dashboard functionality
Donation receipts and email notifications
Improved monitoring and logging
License

This project was developed for Sri Balaganapathi Seva Mandali as a temple donation management application.
