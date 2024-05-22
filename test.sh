curl --header "Content-Type: application/json" \
    --request POST \
    --data '{"repo":"https://github.com/jdkandersson/test-github-monitor","branch":"main"}' \
    http://localhost:5000/test