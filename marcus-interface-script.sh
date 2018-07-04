#!/bin/bash

echo $0 $@ >> /tmp/m.log

cat - >> /tmp/m.log

#status:
#- deployed
#- removed
#- rejected
#- failed

cat << EOF
{
    "status":"failed",
    "message":"this is a message",
    "questionnaire ": {"key":"value"},
    "credentials": {"key":"value"}
}
EOF


exit 0
input:

{
    "state_target": "deployed",
    "user": {
        "email": "",
        "groups": [
            {
                "name": "/"
            },
            {
                "name": "/myExampleColab"
            },
            {
                "name": "/hdfdev"
            }
        ],
        "userinfo": {
            "eduPersonEntitlement": [
                "urn:test:hdf:group:root#unity.helmholtz-data-federation.de",
                "urn:test:hdf:group:root:myExampleColab#unity.helmholtz-data-federation.de"
            ],
            "email": "marcus.hardt@kit.edu",
            "email_verified": "true",
            "groups": [
                "/myExampleColab",
                "/hdfdev",
                "/"
            ],
            "name": "Marcus Hardt",
            "preferred_username": "marcus",
            "ssh_key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC4vjkJr6H6eXKE9+dj4epCrcSUQRFih1603/SjJKIA3cpWt0O5TC4qJCQwOcvFXdjCu0Y1YUKrUlmV0D9fezbqNrSEZ30gT5YLhawUT6LukMTKfNLxa5wM7jzAlmhJ4obadTE5G5qpAGz5SbgHRfPdTlctpqmmFeyN/Rw4lgzoJ8+zHFyp2VPB7rCaUdsS+48lkVhYtlIDBogdRLAZp8MpSeHZFjHfpq+XDhHXdKnEtETV2+IQfMxRBj6Bpw7wwWpIkSQuf4VDHTAhb6+KjcBg/TBc46CekKzF6gtKImZZNVIzEXuAW2prHmQRh72+oQFMqhVcnRmDOWGwBEvXzT0R marcus@tuna2013\n",
            "sub": "61230996-664f-4422-9caa-76cf086f0d6c"
        }
    },
    "key": {
        "name": "Kee",
        "key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC4vjkJr6H6eXKE9+dj4epCrcSUQRFih1603/SjJKIA3cpWt0O5TC4qJCQwOcvFXdjCu0Y1YUKrUlmV0D9fezbqNrSEZ30gT5YLhawUT6LukMTKfNLxa5wM7jzAlmhJ4obadTE5G5qpAGz5SbgHRfPdTlctpqmmFeyN/Rw4lgzoJ8+zHFyp2VPB7rCaUdsS+48lkVhYtlIDBogdRLAZp8MpSeHZFjHfpq+XDhHXdKnEtETV2+IQfMxRBj6Bpw7wwWpIkSQuf4VDHTAhb6+KjcBg/TBc46CekKzF6gtKImZZNVIzEXuAW2prHmQRh72+oQFMqhVcnRmDOWGwBEvXzT0R marcus@tuna2013\n"
    },
    "questionnaire": null
}
