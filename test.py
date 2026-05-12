import argon2

hasher = argon2.PasswordHasher()

print(hasher.hash("Password123"))
# $argon2id$v=19$m=65536,t=3,p=4$zaS8265XxlHq5bNg/XmxgA$X1OF9bDN2WijfEyATLsW68Bs9gjWHGJ3sTQXNEc1LJg
# $argon2id$v=19$m=65536,t=3,p=4$/zZZW18KKsVFbQczNTzljw$etlKsU6RR89ltTEAxxhUZwC8I3K0pENjiq4Kdes60t0
