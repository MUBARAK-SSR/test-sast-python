import os
import sys

def create_service(service_name):
    # Define the directory structure for the service
    service_path = os.path.join("app", "services", service_name)
    files = [
        "__init__.py",
        "config.py",
        "constants.py",
        "dependencies.py",
        "main.py",
        "router.py",
        "schemas.py",
        "handlers.py"
    ]

    # Create the service directory
    os.makedirs(service_path, exist_ok=True)

    # Create the service files
    for file_name in files:
        file_path = os.path.join(service_path, file_name)
        with open(file_path, "w") as f:
            f.write("# Placeholder content for {}\n".format(file_name))

    print("Service '{}' created successfully.".format(service_name))

if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "service:create":
        print("Usage: python scaffold.py service:create <service_name>")
        sys.exit(1)
    
    service_name = sys.argv[2]
    create_service(service_name)