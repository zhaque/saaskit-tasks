from setuptools import setup, find_packages

setup(name="django-tasks",
           version="0.1",
           description="Django application providing activities and tasks to twitter users",
           author="Brian Guertin",
           author_email="dev@brianguertin.com",
           packages=find_packages(),
           include_package_data=True,
)

