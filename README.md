# CS50 Final Project - Online Fashion Outlet Store (Ecommerce site)

#### Video Demo: [link](https://drive.google.com/file/d/15-9ly-NG_WVj9YX8d3fNz3g1Trqb2L4F/view?usp=sharing)

#### Description:

MONO Fashion Store is a full-stack e-commerce web application developed using Flask, SQLite, Tailwind CSS, JavaScript, and Stripe. The project was created as my CS50x Final Project and represents the largest and most technically challenging application I have built so far.

The purpose of the project was to build a realistic online clothing store that supports both customer and administrator functionality. Customers are able to register accounts, securely log in, browse products, view individual product pages, manage a shopping basket, place orders using Stripe Checkout, and review previous purchases through their account dashboard. Administrators have access to a separate backend management system where they can add products, modify product details, upload and manage product images, edit customer accounts, and manage administrator permissions.

The project uses Flask as the backend framework alongside SQLite for the database layer. Throughout development I relied heavily on raw SQL queries rather than an ORM such as SQLAlchemy. Although this approach required more manual query writing, it significantly improved my understanding of relational databases, table relationships, joins, and how data flows throughout a web application. The database itself contains multiple related tables including users, admins, products, product_images, orders, and order_items.

One of the most important aspects of the project for me personally was authentication and session handling. Before starting this project, I only had limited experience with Flask sessions through CS50 Finance. During development I rebuilt much of the authentication system myself in order to better understand how sessions work internally. I implemented separate authentication systems for both customers and administrators, including custom decorators such as login_required and admin_required to restrict access to protected routes.

Passwords are securely stored using Argon2 hashing rather than plain text storage. I specifically chose Argon2 because it is currently considered one of the strongest password hashing algorithms available. Whilst implementing authentication, I also learnt more about session security, cookie handling, cache control, and why validating user input throughout an application is so important.

Another major learning experience was integrating Stripe payments. Prior to this project I had never worked with any payment platform or API. I spent time reading Stripe documentation and experimenting with Stripe’s sandbox testing environment in order to understand how payment sessions work and how order data should be handled securely before and after checkout. The application creates pending orders before redirecting users to Stripe Checkout, then updates the order status once payment succeeds. Although this implementation still has improvements planned for future versions, such as Stripe webhooks and more advanced validation, building the current payment system taught me a huge amount about how real-world web applications process transactions securely.

The project also integrates Cloudinary for image hosting and management. Rather than storing image files directly inside the application, uploaded product images are stored externally and their hosted URLs are saved within the database. This keeps the project lighter, improves scalability, and more closely reflects how production applications handle media storage. Administrators are able to upload multiple product images, assign primary product images, and remove images individually through the backend management system.

Throughout development I attempted to separate reusable backend logic into a dedicated helpers.py file. This allowed routes inside app.py to remain cleaner whilst centralising database queries, authentication helpers, and reusable functionality. Whilst the overall structure of the project is still far from perfect, organising code in this way taught me the importance of maintainability and reusable backend architecture.

For the frontend, I used Tailwind CSS rather than traditional CSS styling. Tailwind is something I am still actively learning, but I wanted to begin moving away from writing large custom CSS files because utility-first styling makes responsive design significantly faster and easier to manage. The current frontend design is not my strongest work visually, largely because much of the project was developed within a relatively short timeframe whilst I was simultaneously learning several new technologies. My primary focus throughout development was functionality, backend logic, database relationships, and security rather than producing a polished commercial-level interface. Even so, using Tailwind CSS massively improved my workflow and helped me understand responsive web design more effectively.

The project was developed very iteratively, and many features required substantial debugging and redesigning before working correctly. Some of the most difficult areas included:

Managing Flask sessions correctly
Understanding how to structure reusable helper functions
Building secure login systems
Handling cart data safely
Managing image uploads
Understanding SQL joins and database relationships
Integrating Stripe payments securely
Handling role-based administrator permissions
Dynamically rendering product data across multiple pages

Whilst building the project I also spent time learning JavaScript through the “30 Days of JavaScript” course by Asabeneh Yetayeh. Although I did not use advanced JavaScript heavily within this version of the application, learning the language alongside development helped me better understand frontend interactions and how I may improve the project in future iterations.

This project also changed the way I approach learning software development. Rather than relying solely on tutorials, I found that building practical projects and solving real implementation problems taught me significantly more. I used AI tools occasionally during development for debugging assistance, troubleshooting, security discussions, and understanding implementation concepts, but I always attempted to build functionality independently first before seeking guidance. Over time I became much more confident debugging problems myself and understanding why solutions worked rather than simply copying code.

At the moment, the project runs locally using SQLite, but I am currently working on deploying an online version using Render for hosting and Supabase as a managed online database solution. Moving towards deployment has introduced another layer of learning around environment variables, production configuration, cloud hosting, database migration, and infrastructure separation. I am also interested in eventually rebuilding parts of the project using SQLAlchemy and more advanced Flask design patterns after gaining more experience.

There are still many improvements I would like to implement in future versions of the application, including:

Improved frontend design and animations
Light and dark mode support
Better form validation
Password reset functionality
Stripe webhook verification
Improved stock management
More advanced order management
CSRF protection
Better project structure using Flask blueprints
Migration from SQLite to PostgreSQL/Supabase
Refactoring backend architecture for scalability

Although this project is not perfect, it represents a major step forward in my understanding of backend development, databases, authentication, security, API integration, and full-stack application design. More importantly, it helped me become far more comfortable building large projects independently and taught me how real-world web applications are structured and managed.
