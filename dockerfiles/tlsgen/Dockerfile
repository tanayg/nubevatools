FROM alpine


RUN apk update && apk add wget && apk add bash
RUN mkdir /opt/nubevaTools
RUN wget -O /opt/nubevaTools/awsGenerateTLSonce.sh https://raw.githubusercontent.com/nubevalabs/NubevaTools/master/awsGenerateTLSonce.sh
RUN chmod +x /opt/nubevaTools/awsGenerateTLSonce.sh
WORKDIR /opt/nubevaTools

CMD /opt/nubevaTools/awsGenerateTLSonce.sh
