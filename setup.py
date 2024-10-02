import setuptools

setuptools.setup(     
     name="LabTable",     
     version="1.0.0",
     python_requires=">=3.6.8",   
     packages=["LabTable", "LabTable.Model", "LabTable.BrickDetection", "LabTable.InputStream", "LabTable.BrickHandling"],
     package_data={'LabTable': ['resources/*/*.png']},
)