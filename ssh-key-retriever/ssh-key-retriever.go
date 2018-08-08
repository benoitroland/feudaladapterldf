package main

import (
	"crypto/tls"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"os"
	"strings"

	kingpin "gopkg.in/alecthomas/kingpin.v2"
)

type (
	AttributeStore struct {
		UserName   string `json:"urn:oid:0.9.2342.19200300.100.1.1"`
		BwidmOrgId string `json:"http://bwidm.de/bwidmOrgId"`
	}
	SshKey struct {
		KeyName  string `json:"name"`
		KeyValue string `json:"value"`
	}
	GenericStore struct {
		SshKey string `json:"ssh_key"`
	}
	LDFUserInfo struct {
		AttributeStore AttributeStore `json:"attributeStore"`
		GenericStore   GenericStore   `json:"genericStore"`
		UidNumber      uint           `json:"uidNumber"`
	}
	config struct {
		BaseUrl      string `json:"BaseUrl"`
		RestUser     string `json:"RestUser"`
		RestPassword string `json:"RestPasswd"`
	}
)

var (
	app = kingpin.New(
		"ssh-key-retriever",
		"Client for getting ssh keys from a rest interface. Matches against <bwidmOrgId>_<username>",
	).Author(
		"Marcus Hardt and Lukas Burgey",
	).Version(
		"0.0.2",
	)
	incomingUserName = app.Arg("username", "username to obtain the keys for").Required().String()
	verbose          = app.Flag("verbose", "Verbosity").Bool()
)

func getSshKeys(b string) (sk []SshKey, err error) {
	tmp := strings.Replace(b, "'", "\"", -1)
	j := []byte(tmp)
	err = json.Unmarshal(j, &sk)
	if err != nil {
		log.Fatal(err)
	}
	return
}

func (l LDFUserInfo) String() (s string) {
	//s += l.GenericStore.SshKey
	tmp := strings.Replace(l.GenericStore.SshKey, "'", "\"", -1)
	SshKeys, _ := getSshKeys(tmp)

	for _, sshKey := range SshKeys {
		//fmt.Printf(">>>>>> %v <<<<<<<<<\n", sshKey.KeyValue)
		s += sshKey.KeyValue + "\n"
	}
	return
}

func getConfig(configFiles []string) (c config, err error) {
	ConfigFile := ""
	for _, ConfigFile = range configFiles {
		if _, err := os.Stat(ConfigFile); err == nil {
			// return if the current ConfigFile exists, so we can use it
			// later
			break
		}
	}
	if *verbose {
		log.Printf("[Conf] using config: %s", ConfigFile)
	}
	bs, err := ioutil.ReadFile(ConfigFile)
	if err != nil {
		if *verbose {
			log.Printf("Error reading config file: %s", err)
		}
		return
	}

	err = json.Unmarshal(bs, &c)
	if err != nil {
		if *verbose {
			log.Printf("Error parsing config file: %s", err)
		}
		return
	}

	if c.BaseUrl == "" {
		log.Fatalf("[Conf] No 'BaseUrl' in config")
	}
	if c.RestUser == "" {
		log.Fatalf("[Conf] No 'RestUser' in config")
	}
	if c.RestUser == "xxxxxxx" { // default value in example config
		log.Fatalf("[Conf] Invalid 'RestUser' 'xxxxxxx' in config")
	}
	if c.RestPassword == "" {
		log.Fatalf("[Conf] No 'RestPassword' in config")
	}
	if c.RestPassword == "xxxxxxxxxxxxx" { // default value in example config
		log.Fatalf("[Conf] Invalide 'RestPassword' 'xxxxxxxxxxxxx' in config")
	}

	return
}

func getUserInfos(username string, config config) (us []LDFUserInfo) {
	client := http.DefaultClient
	_, set := os.LookupEnv("HTTPS_INSECURE")
	if set {
		tr := &http.Transport{
			TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
		}
		client = &http.Client{Transport: tr}
	}

	url := config.BaseUrl + "external-user/find/attribute/urn:oid:0.9.2342.19200300.100.1.1/" + username
	req, err := http.NewRequest("GET", url, nil)
	req.SetBasicAuth(config.RestUser, config.RestPassword)

	response, err := client.Do(req)

	if err != nil {
		log.Printf("%s", err)
		os.Exit(1)
	}

	responseData, err := ioutil.ReadAll(response.Body)
	if err != nil {
		log.Fatal(err)
	}

	err = json.Unmarshal(responseData, &us)
	if err != nil {
		log.Fatal(err)
	}
	return
}

func main() {
	// get arguments
	kingpin.MustParse(app.Parse(os.Args[1:]))

	uInfos := strings.Split(*incomingUserName, "_")
	if len(uInfos) < 2 {
		log.Printf("Could not split incoming user name: %s", *incomingUserName)
		os.Exit(0)
	}
	bwidmOrgId := uInfos[0]
	username := strings.Join(uInfos[1:], "_")

	configFiles := []string{"ssh-key-retriever.json.conf", "/etc/ssh-key-retriever.json.conf"}
	config, err := getConfig(configFiles)
	if err != nil {
		log.Fatal(err)
	}

	userinfos := getUserInfos(username, config)

	for _, userinfo := range userinfos {
		if userinfo.AttributeStore.BwidmOrgId == bwidmOrgId {
			fmt.Printf("%v", userinfo)
		}
	}
}
