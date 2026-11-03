# Application

Application services coordinate use cases and depend on focused contracts for outside capabilities.

`ifix_acquisition.py` coordinates the explicit IFIX source download, local storage operation and complete/partial result. It accepts a source client and storage adapter, so request behavior and file safety can be tested independently. It is invoked by `python -m backend.src.acquisition.ifix`; importing it does not perform network or file operations.
