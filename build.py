from conan.packager import ConanMultiPackager, split_colon_env
import os, re, platform, copy


def get_value_from_recipe(search_string):
    with open("conanfile.py", "r") as conanfile:
        contents = conanfile.read()
        result = re.search(search_string, contents)
    return result

def get_name_from_recipe():
    return get_value_from_recipe(r'name\s*=\s*"(\S*)"').groups()[0]

def get_version_from_recipe():
    return get_value_from_recipe(r'version\s*=\s*"(\S*)"').groups()[0]

def get_default_vars():
    username = os.getenv("CONAN_USERNAME", "bincrafters")
    channel = os.getenv("CONAN_CHANNEL", "testing")
    version = get_version_from_recipe()
    return username, channel, version

def is_ci_running():
    return os.getenv("APPVEYOR_REPO_NAME","") or os.getenv("TRAVIS_REPO_SLUG","")

def get_ci_vars():
    reponame_a = os.getenv("APPVEYOR_REPO_NAME","")
    repobranch_a = os.getenv("APPVEYOR_REPO_BRANCH","")

    reponame_t = os.getenv("TRAVIS_REPO_SLUG","")
    repobranch_t = os.getenv("TRAVIS_BRANCH","")

    username, _ = reponame_a.split("/") if reponame_a else reponame_t.split("/")
    channel, version = repobranch_a.split("/") if repobranch_a else repobranch_t.split("/")
    return username, channel, version

def get_env_vars():
    return get_ci_vars() if is_ci_running() else get_default_vars()

def get_os():
    return platform.system().replace("Darwin", "Macos")

def get_remotes():
    user_remote = "https://api.bintray.com/conan/{0}/public-conan".format(username)
    bincrafters_remote = 'https://api.bintray.com/conan/bincrafters/public-conan'
    remotes = [user_remote, bincrafters_remote]

    # If the user supplied a remote manually we give him priority
    # e.g. maybe he is trying to override user_remote or the bincrafters_remote repo.
    remote_env = split_colon_env("CONAN_REMOTES")
    if remote_env:
        remotes = remote_env + remotes
    return remotes

if __name__ == "__main__":
    name = get_name_from_recipe()
    username, channel, version = get_env_vars()
    reference = "{0}/{1}".format(name, version)
    upload = "https://api.bintray.com/conan/{0}/public-conan".format(username)

    builder = ConanMultiPackager(
        username=username, 
        channel=channel, 
        reference=reference, 
        upload=upload,
        remotes=get_remotes(),
        upload_only_when_stable=True, 
        stable_branch_pattern="stable/*")
        
    builder.add_common_builds(shared_option_name="%s:shared" % name, pure_c=True)

    # add macos builds with openssl too
    builds = []
    for settings, options, env_vars, build_requires in builder.builds:
        builds.append([settings, options, env_vars, build_requires])
        if settings["compiler"] == "apple-clang" and settings["build_type"] == "Release":
            new_options = copy.copy(options)
            new_options["libcurl:darwin_ssl"] = False
            builds.append([settings, new_options, env_vars, build_requires])
    builder.builds = builds

    builder.run()
